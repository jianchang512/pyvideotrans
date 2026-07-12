"""vLLM-accelerated inference for ConfuciusTTS.

This is the vLLM counterpart of ``confuciustts/cli/inference.py``. It keeps the
same two-stage pipeline (Text → Semantic → Audio) but replaces the HuggingFace
``generate`` call in the T2S stage with a vLLM ``AsyncLLM`` engine for faster,
asynchronous decoding, and adds streaming synthesis on top.

Pipeline:
    1. Load reference audio → extract style / semantic conditioning
    2. Text → Semantic tokens (T2S model, served by vLLM)
    3. Semantic tokens → Mel-spectrogram (S2A model, flow matching)
    4. Mel → Waveform (BigVGAN vocoder)
"""

import os
import sys
import uuid
import time
from typing import AsyncIterator, Optional

import logging
import safetensors.torch
import soundfile as sf
import torch
import torchaudio
import yaml
from transformers import AutoTokenizer, SeamlessM4TFeatureExtractor, Wav2Vec2BertModel
from huggingface_hub import hf_hub_download

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _replace_prefix(d: dict, old: str, new: str) -> None:
    """Recursively rewrite string values in a (possibly nested) dict that start
    with ``old`` so their prefix becomes ``new``.

    Used to redirect the checkpoint paths in the config from the default
    ``./checkpoints`` location to a user-supplied ``model_dir``.
    """
    for k, v in d.items():
        if isinstance(v, str) and v.startswith(old):
            d[k] = new + v[len(old):]
        elif isinstance(v, dict):
            _replace_prefix(v, old, new)


# Importing this module registers the custom Text2SemanticVLLM architecture and
# patches vLLM's GPUModelRunner for TTS position handling. Must run before the
# engine is constructed, hence the top-level import.
import confuciustts.llm.patch_vllm

from vllm import SamplingParams, TokensPrompt
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.v1.engine.async_llm import AsyncLLM

from external.bigvgan.bigvgan import BigVGAN
from external.campplus import CAMPPlus

from confuciustts.flow.flow import MaskedDiffWithXvec, MaskedDiffWithXvecConfig
from confuciustts.frontend.text_normalizer import TextNormalizer
from confuciustts.llm.llm import Text2Semantic, Text2SemanticConfig
from confuciustts.llm.llm_vllm import PLACEHOLDER_TOKEN
from confuciustts.utils.audio_features import mel_spectrogram
from confuciustts.utils.audio_post import cross_fade_concat
from confuciustts.utils.text_utils import LANGUAGE_TOKEN_MAP


class ConfuciusTTSVLLM:
    """Zero-shot multilingual TTS with vLLM-accelerated semantic generation.

    Mirrors :class:`confuciustts.cli.inference.ConfuciusTTS` but drives the T2S
    stage through a vLLM ``AsyncLLM`` engine, which enables asynchronous decoding
    and token-level streaming. The S2A (flow matching) and vocoder stages are
    unchanged.

    Args:
        config_path: Path to the YAML config with model paths and audio params
        gpu_memory_utilization: Fraction of GPU memory reserved for the vLLM engine
        device: Device for the non-vLLM modules ("cuda" or "cpu")
        model_dir: Optional root that overrides the "./checkpoints" prefix in config
    """

    def __init__(
        self,
        config_path: str = "config/inference_config.yaml",
        gpu_memory_utilization: float = 0.4,
        device: str = "cuda",
        model_dir: Optional[str] = None,
    ):
        self.device = torch.device(device)

        # Load config and, if a model_dir is given, repoint checkpoint paths at it.

        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        _model_dir = model_dir or os.environ.get("MODEL_DIR")
        if _model_dir:
            _model_dir = os.path.abspath(_model_dir)
            _replace_prefix(self.cfg["paths"], "./checkpoints", _model_dir)

        paths = self.cfg["paths"]

        # Audio / mel-spectrogram parameters shared across the pipeline.
        self.sample_rate = self.cfg["audio"]["target_sample_rate"]
        self.n_mels = self.cfg["audio"]["n_mels"]
        self.n_fft = self.cfg["audio"]["n_fft"]
        self.hop_length = self.cfg["audio"]["hop_length"]
        self.win_length = self.cfg["audio"]["win_length"]
        self.fmin = self.cfg["audio"]["fmin"]
        self.fmax = self.cfg["audio"]["fmax"]

        # BOS/EOS token ids for the semantic sequence.
        t2s_cfg = self.cfg["t2s_model"]
        self._bos = t2s_cfg["start_semantic_token"]
        self._eos = t2s_cfg["stop_semantic_token"]

        self.normalizer = TextNormalizer()
        self.tokenizer = AutoTokenizer.from_pretrained(paths["tokenizer_path"])

        # Wav2Vec2-BERT for semantic feature extraction, plus its normalization stats.
        self.feature_extractor = SeamlessM4TFeatureExtractor.from_pretrained(
            paths["w2v_bert_path"]
        )
        self.w2v_model = (
            Wav2Vec2BertModel.from_pretrained(paths["w2v_bert_path"]).eval().to(self.device)
        )
        stats = torch.load(paths["w2v_stat"], map_location="cpu")
        self.semantic_mean = stats["mean"].to(self.device)
        self.semantic_std = torch.sqrt(stats["var"]).to(self.device)

        # CAMPPlus speaker/style encoder. Prefer a local checkpoint, otherwise
        # fall back to downloading the weights from the HuggingFace Hub.
        spk_cfg = paths["style_encoder"]
        self.style_encoder = CAMPPlus(**spk_cfg.get("init_args", {}))
        spk_ckpt_field = "checkpoint_path" if "checkpoint_path" in spk_cfg else None
        if spk_ckpt_field and os.path.exists(spk_cfg[spk_ckpt_field]):
            spk_ckpt_path = spk_cfg[spk_ckpt_field]
        else:
            spk_ckpt_path = hf_hub_download(
                "funasr/campplus", filename=spk_cfg["checkpoint"]
            )
        spk_state = torch.load(spk_ckpt_path, map_location="cpu")
        if isinstance(spk_state, dict) and "state_dict" in spk_state:
            spk_state = spk_state["state_dict"]
        self.style_encoder.load_state_dict(spk_state, strict=False)
        self.style_encoder.eval().to(self.device)

        # Resolve the T2S checkpoint: relative paths are anchored to the config
        # dir; if it still does not exist, download it from the Hub.
        t2s_ckpt = paths.get("t2s_checkpoint_path") or paths["t2s_checkpoint"]
        if not os.path.isabs(t2s_ckpt):
            t2s_ckpt = os.path.join(os.path.dirname(config_path), "..", t2s_ckpt)
            t2s_ckpt = os.path.abspath(t2s_ckpt)
        if not os.path.exists(t2s_ckpt):
            t2s_ckpt = hf_hub_download(
                "netease-youdao/Confucius4-TTS", filename=paths["t2s_checkpoint"]
            )

        # Same resolution logic for the S2A checkpoint.
        s2a_ckpt = paths.get("s2a_checkpoint_path") or paths["s2a_checkpoint"]
        if not os.path.isabs(s2a_ckpt):
            s2a_ckpt = os.path.join(os.path.dirname(config_path), "..", s2a_ckpt)
            s2a_ckpt = os.path.abspath(s2a_ckpt)
        if not os.path.exists(s2a_ckpt):
            s2a_ckpt = hf_hub_download(
                "netease-youdao/Confucius4-TTS", filename=paths["s2a_checkpoint"]
            )

        # vLLM loads a model from a directory. We assemble a lightweight
        # "t2s_vllm" model dir containing a config.json, tokenizer files, and a
        # symlink to the real T2S weights, so vLLM can serve our custom
        # Text2SemanticVLLM architecture without duplicating the checkpoint.
        if _model_dir:
            vllm_model_dir = os.path.join(_model_dir, "t2s_vllm")
        else:
            vllm_model_dir = os.path.join(
                os.path.dirname(config_path), "..", "checkpoints", "t2s_vllm"
            )
        vllm_model_dir = os.path.abspath(vllm_model_dir)

        # Write a GPT2-style HF config describing the T2S transformer so vLLM can
        # instantiate the model. Only created once.
        os.makedirs(vllm_model_dir, exist_ok=True)
        _vllm_config_path = os.path.join(vllm_model_dir, "config.json")
        if not os.path.exists(_vllm_config_path):
            import json
            _vllm_config = {
                "architectures": ["Text2SemanticVLLM"],
                "model_type": "gpt2",
                "activation_function": "gelu_new",
                "n_embd": 1280,
                "n_head": 20,
                "n_layer": 24,
                "n_positions": 2041,
                "n_ctx": 2041,
                "vocab_size": 8194,
                "n_semantic_positions": 1520,
                "bos_token_id": 8192,
                "eos_token_id": 8193,
                "use_cache": True,
                "layer_norm_epsilon": 1e-5,
                "initializer_range": 0.02,
                "scale_attn_weights": True,
                "reorder_and_upcast_attn": False,
                "scale_attn_by_inverse_layer_idx": False,
                "add_cross_attention": False,
            }
            with open(_vllm_config_path, "w") as f:
                json.dump(_vllm_config, f, indent=2)

        # Symlink the tokenizer files into the vLLM model dir (vLLM loads the
        # tokenizer from the same directory as the model).
        _tokenizer_path = paths["tokenizer_path"]
        if not os.path.isabs(_tokenizer_path):
            _tokenizer_path = os.path.join(
                os.path.dirname(config_path), "..", _tokenizer_path
            )
            _tokenizer_path = os.path.abspath(_tokenizer_path)
        _tokenizer_files = [
            "tokenizer.json", "tokenizer.model", "tokenizer_config.json",
            "special_tokens_map.json", "vocab.json", "merges.txt",
        ]
        for _tf in _tokenizer_files:
            _dst = os.path.join(vllm_model_dir, _tf)
            if os.path.lexists(_dst):
                continue
            _src = os.path.join(_tokenizer_path, _tf)
            if os.path.exists(_src):
                try:
                    os.symlink(_src, _dst)
                except OSError:
                    pass

        # Point model.safetensors at the real T2S checkpoint via symlink. If the
        # filesystem does not support symlinks, fall back to a temp dir that
        # copies the config/tokenizer files alongside a symlinked weight file.
        import shutil, tempfile
        _weights_link = os.path.join(vllm_model_dir, "model.safetensors")
        _link_ok = (
            os.path.lexists(_weights_link)
            and os.path.islink(_weights_link)
            and os.readlink(_weights_link) == t2s_ckpt
        )
        if not _link_ok:
            try:
                if os.path.lexists(_weights_link):
                    os.remove(_weights_link)
                os.symlink(t2s_ckpt, _weights_link)
            except OSError:
                _tmp_dir = tempfile.mkdtemp(prefix="confucius_t2s_vllm_")
                for _fn in os.listdir(vllm_model_dir):
                    _fp = os.path.join(vllm_model_dir, _fn)
                    if os.path.isfile(_fp) and not _fn.endswith(".safetensors"):
                        shutil.copy2(_fp, os.path.join(_tmp_dir, _fn))
                os.symlink(t2s_ckpt, os.path.join(_tmp_dir, "model.safetensors"))
                vllm_model_dir = _tmp_dir

        # Build the async vLLM engine. enable_mm_embeds lets us feed precomputed
        # prefix embeddings (speaker + text + BOS) as a "multimodal" input;
        # chunked prefill is disabled because the whole prefix arrives at once.
        engine_args = AsyncEngineArgs(
            model=vllm_model_dir,
            tensor_parallel_size=1,
            dtype="float16",
            gpu_memory_utilization=gpu_memory_utilization,
            async_scheduling=True,
            enable_mm_embeds=True,
            enable_chunked_prefill=False,
        )
        self.llm = AsyncLLM.from_engine_args(engine_args)

        # Decoding parameters for semantic-token generation. Stops on EOS.
        self.sampling_params = SamplingParams(
            temperature=0.8,
            top_p=0.8,
            top_k=30,
            repetition_penalty=10.0,
            max_tokens=self.cfg["t2s_model"]["max_semantic_seq_lens"] - 2,
            stop_token_ids=[self._eos],
            ignore_eos=True,
            include_stop_str_in_output=True,
        )

        # Also keep a native (non-vLLM) copy of the T2S model. vLLM only produces
        # semantic token ids; this copy is used to recompute the LM latent that
        # conditions the S2A stage (see _extract_latent / _build_prefix_embeds).
        t2s_config = Text2SemanticConfig(**t2s_cfg)
        self.t2s_model = Text2Semantic(t2s_config)
        state = safetensors.torch.load_file(t2s_ckpt, device="cpu")
        self.t2s_model.load_state_dict(state)
        self.t2s_model.eval().to(self.device)

        # S2A flow-matching model: semantic tokens + latent → mel-spectrogram.
        s2a_config = MaskedDiffWithXvecConfig(**self.cfg["s2a_model"])
        self.s2a_model = MaskedDiffWithXvec(s2a_config)
        self.s2a_model.load_state_dict(
            torch.load(s2a_ckpt, map_location="cpu", weights_only=False)
        )
        self.s2a_model.eval().to(self.device)

        # BigVGAN vocoder: mel-spectrogram → waveform.
        self.bigvgan = BigVGAN.from_pretrained(paths["vocoder_path"], use_cuda_kernel=False)
        self.bigvgan.remove_weight_norm()
        self.bigvgan.eval().to(self.device)


    def _load_prompt(self, prompt_wav: str, max_seconds: int = 30):
        """Load reference audio and resample to 16kHz and the target sample rate.

        The audio is downmixed to mono and truncated to ``max_seconds``.

        Args:
            prompt_wav: Path to the reference audio file
            max_seconds: Maximum reference length to keep, in seconds

        Returns:
            Tuple of (wav_16k, wav_tgt): waveforms at 16kHz (for the encoders)
            and at the target sample rate (for the reference mel).
        """
        data, sr = sf.read(prompt_wav, dtype="float32", always_2d=True)
        wav = torch.from_numpy(data.T)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        max_samples = sr * max_seconds
        if wav.shape[1] > max_samples:
            wav = wav[:, :max_samples]
        target_sr = self.sample_rate
        if sr != 16000:
            from torchaudio.functional import resample as ta_resample
            wav_16k = ta_resample(wav, sr, 16000)
        else:
            wav_16k = wav
        if sr != target_sr:
            from torchaudio.functional import resample as ta_resample
            wav_tgt = ta_resample(wav, sr, target_sr)
        else:
            wav_tgt = wav
        return wav_16k, wav_tgt

    def _ref_mel(self, wav_tgt: torch.Tensor) -> torch.Tensor:
        """Extract the reference mel-spectrogram used as S2A prompt conditioning.

        Args:
            wav_tgt: Waveform at the target sample rate, shape (C, T)

        Returns:
            Mel-spectrogram with shape (1, T_mel, n_mels)
        """
        mel = mel_spectrogram(
            wav_tgt.to(self.device).float(),
            sample_rate=self.sample_rate,
            n_fft=self.n_fft, hop_length=self.hop_length, win_length=self.win_length,
            n_mels=self.n_mels, fmin=self.fmin, fmax=self.fmax,
        )
        return mel.transpose(1, 2).contiguous()

    @torch.no_grad()
    def _extract_semantic(self, wav_16k: torch.Tensor) -> torch.Tensor:
        """Extract normalized semantic features from the reference using Wav2Vec2-BERT.

        Args:
            wav_16k: Waveform at 16kHz, shape (1, T)

        Returns:
            Normalized layer-17 hidden states, shape (1, T_feat, D)
        """
        inputs = self.feature_extractor(
            wav_16k.squeeze(0).cpu().numpy(), sampling_rate=16000, return_tensors="pt"
        )
        input_features = inputs["input_features"].to(self.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        outputs = self.w2v_model(
            input_features=input_features,
            attention_mask=attention_mask,
            output_hidden_states=True,
        )
        feats = outputs.hidden_states[17].detach().clone()  # Layer 17 hidden states
        del outputs, input_features, attention_mask
        return (feats - self.semantic_mean) / self.semantic_std

    @torch.no_grad()
    def _extract_style(self, wav_16k: torch.Tensor) -> torch.Tensor:
        """Extract the speaker style embedding using the CAMPPlus encoder.

        Args:
            wav_16k: Waveform at 16kHz, shape (1, T)

        Returns:
            Style embedding, shape (1, D_style)
        """
        fbank = torchaudio.compliance.kaldi.fbank(
            wav_16k, num_mel_bins=80, sample_frequency=16000, dither=0.0
        )
        fbank = fbank - fbank.mean(dim=0, keepdim=True)
        return self.style_encoder(fbank.unsqueeze(0).to(self.device))


    @torch.no_grad()
    def _build_prefix_embeds(
        self,
        text_inputs: torch.Tensor,
        condition_vector: torch.Tensor,
    ) -> torch.Tensor:
        """Build the prefix embeddings that seed vLLM decoding.

        The T2S transformer is prompted with a prefix of
        ``[speaker | text | BOS]`` embeddings rather than token ids. These are
        precomputed here with the native model and handed to vLLM as multimodal
        embeds (see ``_generate_semantic``).

        Args:
            text_inputs: Tokenized text ids, shape (1, T_text)
            condition_vector: Semantic conditioning features from the reference

        Returns:
            Prefix embeddings, shape (1, 1 + T_text + 1, D)
        """
        # Speaker conditioning embedding (one token).
        condition_emb = self.t2s_model.speaker_encoder(condition_vector).unsqueeze(1)

        # Text embeddings with positional encoding.
        text_emb = self.t2s_model.text_projector(text_inputs)
        text_emb = self.t2s_model.text_position_embedding(text_emb)

        # BOS embedding for the semantic sequence, at position 0.
        bos_tok = torch.full((1, 1), self._bos, dtype=torch.long, device=self.device)
        bos_emb = self.t2s_model.semantic_embedding(bos_tok)
        bos_pos = self.t2s_model.semantic_position_embedding.get_fixed_embedding(
            0, self.device
        )
        bos_emb = bos_emb + bos_pos

        return torch.cat([condition_emb, text_emb, bos_emb], dim=1)


    async def _generate_semantic(
        self,
        text_inputs: torch.Tensor,
        condition_vector: torch.Tensor,
        verbose: bool = False,
    ) -> torch.Tensor:
        """Generate the full semantic-token sequence for one text segment via vLLM.

        Args:
            text_inputs: Tokenized text ids, shape (1, T_text)
            condition_vector: Semantic conditioning features from the reference
            verbose: Print the raw vLLM output token ids

        Returns:
            Semantic token ids (BOS/EOS stripped), shape (1, T_semantic)
        """
        # Precompute the prefix embeddings and pass them to vLLM as multimodal
        # embeds keyed by the "!" placeholder prompt.
        inputs_embeds = self._build_prefix_embeds(text_inputs, condition_vector)

        multi_modal_data = {
            "audio": {"audio_embeds": [inputs_embeds.squeeze(0).cpu()]}
        }
        del inputs_embeds
        torch.cuda.empty_cache()

        tokens_prompt = TokensPrompt(
            prompt=PLACEHOLDER_TOKEN,
            multi_modal_data=multi_modal_data,
        )
        gen_request_id = uuid.uuid4().hex
        output_gen = self.llm.generate(
            tokens_prompt, sampling_params=self.sampling_params, request_id=gen_request_id
        )
        # Drain the async generator; the last item holds the full output.
        async for output in output_gen:
            pass
        token_ids = list(output.outputs[0].token_ids)
        del output
        if verbose:
            print(f"  [vLLM] raw output token_ids ({len(token_ids)}): {token_ids[:10]}...{token_ids[-5:]}")
        # Strip trailing EOS, drop any BOS/EOS, and clamp to valid semantic ids.
        while token_ids and token_ids[-1] == self._eos:
            token_ids.pop()
        token_ids = [t for t in token_ids if t != self._bos and t != self._eos]
        token_ids = [min(t, self._bos - 1) for t in token_ids]

        return torch.tensor(token_ids, dtype=torch.long, device=self.device).unsqueeze(0)

    async def _generate_semantic_stream(
        self,
        text_inputs: torch.Tensor,
        condition_vector: torch.Tensor,
        first_chunk_size: int,
        chunk_size: int,
    ) -> AsyncIterator[tuple]:
        """Stream cumulative semantic tokens as vLLM decodes them.

        Yields the whole sequence generated so far whenever enough new tokens
        have accumulated (``first_chunk_size`` for the first chunk, then
        ``chunk_size``), so downstream S2A can start synthesizing before the LLM
        finishes.

        Args:
            text_inputs: Tokenized text ids, shape (1, T_text)
            condition_vector: Semantic conditioning features from the reference
            first_chunk_size: Token count that triggers the first yield
            chunk_size: Token count between subsequent yields

        Yields:
            Tuple ``(cumulative_ids, is_final, vllm_ms)`` where ``cumulative_ids``
            is the cleaned token list so far, ``is_final`` marks the last chunk,
            and ``vllm_ms`` is the decode time since the previous yield.
        """
        inputs_embeds = self._build_prefix_embeds(text_inputs, condition_vector)
        multi_modal_data = {"audio": {"audio_embeds": [inputs_embeds.squeeze(0).cpu()]}}
        del inputs_embeds
        torch.cuda.empty_cache()

        tokens_prompt = TokensPrompt(
            prompt=PLACEHOLDER_TOKEN,
            multi_modal_data=multi_modal_data,
        )
        gen_request_id = uuid.uuid4().hex
        output_gen = self.llm.generate(
            tokens_prompt, sampling_params=self.sampling_params, request_id=gen_request_id
        )

        def _clean(ids):
            # Drop BOS/EOS and clamp to valid semantic token ids.
            ids = [t for t in ids if t != self._bos and t != self._eos]
            return [min(t, self._bos - 1) for t in ids]

        prev_len = 0            # length of raw output already consumed
        cumulative = []         # cleaned tokens accumulated so far
        yielded_count = 0       # token count at the last yield
        t_chunk = time.time()

        async for output in output_gen:
            # vLLM re-sends the full sequence each step; take only the new tail.
            raw = list(output.outputs[0].token_ids)
            while raw and raw[-1] == self._eos:
                raw = raw[:-1]
            new_tokens = _clean(raw[prev_len:])
            prev_len = len(raw)
            cumulative.extend(new_tokens)

            # Emit as many full chunks as the buffered tokens allow.
            next_threshold = (first_chunk_size if yielded_count == 0
                              else yielded_count + chunk_size)
            while len(cumulative) >= next_threshold:
                vllm_ms = int((time.time() - t_chunk) * 1000)
                t_chunk = time.time()
                yield (list(cumulative), False, vllm_ms)
                yielded_count = len(cumulative)
                next_threshold = yielded_count + chunk_size

        # Flush the remaining tail as the final chunk.
        if len(cumulative) > yielded_count:
            vllm_ms = int((time.time() - t_chunk) * 1000)
            yield (list(cumulative), True, vllm_ms)


    @torch.no_grad()
    def _extract_latent(
        self,
        text_inputs: torch.Tensor,
        semantic_codes: torch.Tensor,
        condition_vector: torch.Tensor,
    ) -> torch.Tensor:
        """Recompute the T2S hidden latent for a given semantic-token sequence.

        vLLM only returns token ids, but the S2A stage additionally needs the
        transformer's hidden states. This runs a single native forward pass over
        ``[BOS | codes | EOS]`` to obtain that latent.

        Args:
            text_inputs: Tokenized text ids, shape (1, T_text)
            semantic_codes: Semantic token ids (no BOS/EOS), shape (1, T_semantic)
            condition_vector: Semantic conditioning features from the reference

        Returns:
            LM latent aligned with ``semantic_codes``, shape (1, T_semantic, D)
        """
        bos = torch.full((1, 1), self._bos, dtype=torch.long, device=self.device)
        eos = torch.full((1, 1), self._eos, dtype=torch.long, device=self.device)
        codes_full = torch.cat([bos, semantic_codes, eos], dim=1)

        latent = self.t2s_model(
            text_inputs=text_inputs,
            text_lengths=torch.tensor([text_inputs.shape[1]], device=self.device),
            semantic_codes=codes_full,
            semantic_lengths=torch.tensor([semantic_codes.shape[1]], device=self.device),
            condition_vector=condition_vector,
            return_latent=True,
        )
        return latent


    @staticmethod
    def _crossfade_chunks(
        wav: torch.Tensor,
        prev_tail: Optional[torch.Tensor],
        chunk_idx: int,
        num_chunks: int,
        overlap_samples: int,
    ) -> tuple:
        """Cross-fade the overlap region between consecutive audio chunks.

        Splits ``overlap_samples`` off the tail of each chunk and linearly
        cross-fades it with the head of the next, so streamed chunks join
        without clicks.

        Args:
            wav: Current chunk waveform, shape (1, T)
            prev_tail: Overlap tail carried from the previous chunk, or None
            chunk_idx: Index of the current chunk
            num_chunks: Total number of chunks
            overlap_samples: Overlap length in samples

        Returns:
            Tuple ``(chunk_out, new_tail)``: the ready-to-emit chunk and the tail
            to carry into the next call (None on the last chunk).
        """
        if overlap_samples <= 0 or num_chunks == 1:
            return wav, None
        if chunk_idx == 0:
            # First chunk: hold back its tail for the next overlap, emit the rest.
            new_tail = wav[:, -overlap_samples:].clone()
            return wav[:, :-overlap_samples], new_tail
        # Blend previous tail with this chunk's head.
        head = wav[:, :overlap_samples]
        fade_out = torch.linspace(1.0, 0.0, overlap_samples, device=wav.device, dtype=wav.dtype)
        fade_in = torch.linspace(0.0, 1.0, overlap_samples, device=wav.device, dtype=wav.dtype)
        crossfaded = prev_tail.to(wav.device, wav.dtype) * fade_out + head * fade_in
        if chunk_idx < num_chunks - 1:
            body = wav[:, overlap_samples:-overlap_samples]
            new_tail = wav[:, -overlap_samples:].clone()
            return torch.cat([crossfaded, body], dim=1), new_tail
        body = wav[:, overlap_samples:]
        return torch.cat([crossfaded, body], dim=1), None


    async def _synth_segment(
        self,
        text: str,
        lang: str,
        semantic_features: torch.Tensor,
        style_embedding: torch.Tensor,
        reference_mel: torch.Tensor,
        n_timesteps: int,
        inference_cfg_rate: float,
        verbose: bool,
        seg_id: Optional[str] = None,
    ) -> torch.Tensor:
        """Synthesize the full waveform for one text segment (non-streaming).

        Runs T2S (vLLM) → latent recompute → S2A → vocoder end to end.

        Args:
            text: Input text segment
            lang: Language code (e.g. "zh", "en")
            semantic_features: Conditioning features from the reference
            style_embedding: Speaker style vector, shape (1, D_style)
            reference_mel: Reference mel-spectrogram, shape (1, T_mel, n_mels)
            n_timesteps: Number of flow-matching steps for S2A
            inference_cfg_rate: Classifier-free guidance rate
            verbose: Print debug info
            seg_id: Optional segment id (for logging)

        Returns:
            Generated waveform, shape (1, T_audio)
        """
        seg_id = seg_id or uuid.uuid4().hex
        # Prompt the T2S model with a language instruction plus the text.
        lang_token = LANGUAGE_TOKEN_MAP.get(lang, f"请用{lang}朗读接下来的文字")
        formatted = f"You are a helpful assistant. {lang_token}:{text}"
        text_inputs = self.tokenizer.encode(formatted, return_tensors="pt").to(self.device)
        # T2S: generate semantic tokens, then recompute the latent for S2A.
        semantic_codes = await self._generate_semantic(text_inputs, semantic_features, verbose=verbose)
        lm_latent = self._extract_latent(text_inputs, semantic_codes, semantic_features)
        del text_inputs

        # Predict target mel length (heuristic: 1.72x semantic length).
        T = semantic_codes.shape[1]
        target_lengths = torch.tensor([int(T * 1.72)], device=self.device)

        # S2A: semantic tokens + latent → mel-spectrogram.
        with torch.no_grad():
            mel = self.s2a_model.inference(
                semantic_token=semantic_codes,
                lm_latent=lm_latent,
                prompt_feat=reference_mel,
                embedding=style_embedding,
                target_feat_len=target_lengths,
                n_timesteps=n_timesteps,
                inference_cfg_rate=inference_cfg_rate,
            )
        del semantic_codes, lm_latent, target_lengths

        # Vocoder: mel → waveform.
        with torch.no_grad():
            audio = self.bigvgan(mel.float().to(self.device)).squeeze(1)
        del mel
        return audio


    async def _synth_segment_stream(
        self,
        text: str,
        lang: str,
        semantic_features: torch.Tensor,
        style_embedding: torch.Tensor,
        reference_mel: torch.Tensor,
        n_timesteps: int,
        inference_cfg_rate: float,
        first_chunk_size_tokens: int,
        chunk_size_tokens: int,
        overlap_tokens: int,
        verbose: bool,
        seg_id: Optional[str] = None,
    ) -> AsyncIterator[torch.Tensor]:
        """Stream the waveform for one text segment chunk by chunk.

        As the T2S stream yields growing semantic sequences, each new chunk is
        run through S2A and the vocoder and emitted immediately. Consecutive
        chunks overlap by ``overlap_tokens`` and are cross-faded (both in the
        latent space and in the waveform) to avoid audible seams.

        Args:
            text: Input text segment
            lang: Language code (e.g. "zh", "en")
            semantic_features: Conditioning features from the reference
            style_embedding: Speaker style vector, shape (1, D_style)
            reference_mel: Reference mel-spectrogram, shape (1, T_mel, n_mels)
            n_timesteps: Number of flow-matching steps for S2A
            inference_cfg_rate: Classifier-free guidance rate
            first_chunk_size_tokens: Tokens before the first chunk is synthesized
            chunk_size_tokens: Tokens per subsequent chunk
            overlap_tokens: Token overlap between chunks (for cross-fade)
            verbose: Print debug info
            seg_id: Optional segment id (for logging)

        Yields:
            Waveform chunks on CPU, each shape (1, T_chunk).
        """
        seg_id = seg_id or uuid.uuid4().hex
        lang_token = LANGUAGE_TOKEN_MAP.get(lang, f"请用{lang}朗读接下来的文字")
        formatted = f"You are a helpful assistant. {lang_token}:{text}"
        text_inputs = self.tokenizer.encode(formatted, return_tensors="pt").to(self.device)

        ratio = 1.72                                          # semantic → mel frame ratio
        overlap = max(0, int(overlap_tokens))                # overlap in semantic tokens
        overlap_samples = int(overlap * ratio) * self.hop_length  # overlap in waveform samples

        chunk_idx = 0
        prev_tail: Optional[torch.Tensor] = None             # waveform tail for cross-fade
        yielded_end = 0                                      # tokens already covered
        prev_overlap_latent: Optional[torch.Tensor] = None   # latent reused in the overlap

        async for cumulative_ids, is_final, vllm_ms in self._generate_semantic_stream(
            text_inputs, semantic_features,
            first_chunk_size=first_chunk_size_tokens,
            chunk_size=chunk_size_tokens,
        ):
            chunk_label = "first_chunk" if chunk_idx == 0 else "inter_chunk"
            cumulative_codes = torch.tensor(
                cumulative_ids, dtype=torch.long, device=self.device
            ).unsqueeze(0)

            # Recompute the latent over the whole sequence so far (S2A needs it).
            lm_latent = self._extract_latent(text_inputs, cumulative_codes, semantic_features)

            # This chunk covers the newly generated tokens plus an overlap back
            # into the previously synthesized region.
            total_N = cumulative_codes.shape[1]
            actual_start = max(0, yielded_end - overlap)
            actual_len = total_N - actual_start

            chunk_codes  = cumulative_codes[:, actual_start:]
            chunk_latent = lm_latent[:, actual_start:].clone()

            # Reuse the previous chunk's overlap latent for continuity.
            if prev_overlap_latent is not None and chunk_idx > 0:
                ol = prev_overlap_latent.shape[1]
                chunk_latent[:, :ol] = prev_overlap_latent

            # Stash this chunk's tail latent for the next iteration's overlap.
            if not is_final and overlap > 0:
                prev_overlap_latent = chunk_latent[:, -overlap:].clone()
            else:
                prev_overlap_latent = None

            target_lengths = torch.tensor([int(actual_len * ratio)], device=self.device)

            # S2A + vocoder for this chunk.
            with torch.no_grad():
                mel = self.s2a_model.inference(
                    semantic_token=chunk_codes,
                    lm_latent=chunk_latent,
                    prompt_feat=reference_mel,
                    embedding=style_embedding,
                    target_feat_len=target_lengths,
                    n_timesteps=n_timesteps,
                    inference_cfg_rate=inference_cfg_rate,
                )
            
            with torch.no_grad():
                wav = self.bigvgan(mel.float().to(self.device)).squeeze(1)
            del mel
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)

            wav_len = wav.shape[1]
            actual_overlap_samples = min(overlap_samples, wav_len // 2)

            # Cross-fade this chunk's waveform against the carried-over tail.
            if chunk_idx == 0:
                # First chunk: emit everything but the tail (kept for next fade).
                if not is_final and wav_len > actual_overlap_samples:
                    wav_out = wav[:, :-actual_overlap_samples]
                    prev_tail = wav[:, -actual_overlap_samples:].clone()
                else:
                    wav_out = wav
                    prev_tail = None
            else:
                if prev_tail is not None:
                    tail_len = prev_tail.shape[1]
                    cf_len = min(tail_len, actual_overlap_samples, wav_len)
                    if cf_len > 0:
                        # Linear cross-fade over the shared region.
                        fade_out = torch.linspace(1.0, 0.0, cf_len, device=wav.device, dtype=wav.dtype)
                        fade_in  = torch.linspace(0.0, 1.0, cf_len, device=wav.device, dtype=wav.dtype)
                        crossfaded = prev_tail[:, :cf_len] * fade_out + wav[:, :cf_len] * fade_in
                        if not is_final and wav_len > cf_len + actual_overlap_samples:
                            wav_out = torch.cat([crossfaded, wav[:, cf_len:-actual_overlap_samples]], dim=1)
                            prev_tail = wav[:, -actual_overlap_samples:].clone()
                        else:
                            wav_out = torch.cat([crossfaded, wav[:, cf_len:]], dim=1)
                            prev_tail = None
                    else:
                        wav_out = wav
                        prev_tail = None
                else:
                    wav_out = wav
                    prev_tail = None

            if wav_out.shape[-1] > 0:
                yield wav_out.cpu()

            yielded_end = total_N
            chunk_idx += 1

        # Emit the final tail that was held back for cross-fading.
        if prev_tail is not None and prev_tail.shape[-1] > 0:
            yield prev_tail.cpu()

        del text_inputs
        torch.cuda.empty_cache()


    async def generate(
        self,
        text: str,
        lang: str,
        prompt_wav: str,
        request_id: Optional[str] = None,
        n_timesteps: int = 25,
        inference_cfg_rate: float = 0.7,
        max_text_tokens_per_segment: int = 80,
        cross_fade_duration: float = 0.3,
        verbose: bool = False,
    ) -> torch.Tensor:
        """Generate speech from text with voice cloning (non-streaming).

        Normalizes and segments the text, synthesizes each segment, then merges
        them with a cross-fade. Returns the full waveform.

        Args:
            text: Input text to synthesize
            lang: Language code (e.g. "zh", "en", "ja", "ko")
            prompt_wav: Path to the reference audio for voice cloning
            request_id: Optional id used to tag segments in logs
            n_timesteps: Number of flow-matching steps for S2A
            inference_cfg_rate: Classifier-free guidance scale
            max_text_tokens_per_segment: Max tokens per segment before splitting
            cross_fade_duration: Silence/cross-fade duration between segments (s)
            verbose: Print processing info

        Returns:
            Generated waveform on CPU, shape (1, T_audio) at the target sample rate
        """
        # Normalize text (punctuation, numbers, etc.).
        text = self.normalizer.normalize(text, language=lang)
        if verbose:
            print(f"[ConfuciusTTSVLLM] normalized: {text}")

        # Extract conditioning from the reference audio.
        wav_16k, wav_tgt = self._load_prompt(prompt_wav)
        semantic_features = self._extract_semantic(wav_16k)
        style_embedding = self._extract_style(wav_16k)
        reference_mel = self._ref_mel(wav_tgt)
        del wav_16k, wav_tgt

        # Split long text into segments.
        segments = self.normalizer.segment_text(
            text,
            tokenize_fn=self.tokenizer.tokenize,
            language=lang,
            max_tokens=max_text_tokens_per_segment,
        )
        if not segments:
            segments = [text]
        if verbose:
            print(f"[ConfuciusTTSVLLM] {len(segments)} segment(s)")

        # Synthesize each segment independently.
        chunks = []
        for i, seg in enumerate(segments):
            seg_id = f"{request_id or uuid.uuid4().hex}_seg{i}"
            if verbose:
                print(f"[ConfuciusTTSVLLM] segment {i+1}/{len(segments)}: {seg!r}")
            logging.info(f"[ConfuciusTTSVLLM] segment {i+1}/{len(segments)}: {seg!r}")
            audio = await self._synth_segment(
                seg, lang, semantic_features, style_embedding, reference_mel,
                n_timesteps, inference_cfg_rate, verbose, seg_id=seg_id,
            )
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            chunks.append(audio.cpu())
            del audio

        del semantic_features, style_embedding, reference_mel
        torch.cuda.empty_cache()

        # Merge the per-segment waveforms with cross-fade.
        result = cross_fade_concat(chunks, self.sample_rate, silence_duration=cross_fade_duration)
        del chunks
        return result.cpu() if result.is_cuda else result

    async def generate_stream(
        self,
        text: str,
        lang: str,
        prompt_wav: str,
        request_id: Optional[str] = None,
        n_timesteps: int = 25,
        inference_cfg_rate: float = 0.7,
        max_text_tokens_per_segment: int = 80,
        first_chunk_size_tokens: int = 25,
        chunk_size_tokens: int = 50,
        overlap_tokens: int = 10,
        cross_fade_duration: float = 0.3,
        verbose: bool = False,
    ) -> AsyncIterator[torch.Tensor]:
        """Generate speech from text with voice cloning, streaming audio chunks.

        Same pipeline as :meth:`generate`, but yields waveform chunks as they are
        produced so callers can start playback with low latency. A short silence
        is inserted between segments.

        Args:
            text: Input text to synthesize
            lang: Language code (e.g. "zh", "en", "ja", "ko")
            prompt_wav: Path to the reference audio for voice cloning
            request_id: Optional id used to tag segments in logs
            n_timesteps: Number of flow-matching steps for S2A
            inference_cfg_rate: Classifier-free guidance scale
            max_text_tokens_per_segment: Max tokens per segment before splitting
            first_chunk_size_tokens: Tokens before the first chunk is synthesized
            chunk_size_tokens: Tokens per subsequent chunk
            overlap_tokens: Token overlap between chunks (for cross-fade)
            cross_fade_duration: Used to size the inter-segment silence
            verbose: Print processing info

        Yields:
            Waveform chunks on CPU, each shape (1, T_chunk).
        """
        # Normalize text (punctuation, numbers, etc.).
        text = self.normalizer.normalize(text, language=lang)
        if verbose:
            print(f"[ConfuciusTTSVLLM-stream] normalized: {text}")

        # Extract conditioning from the reference audio.
        wav_16k, wav_tgt = self._load_prompt(prompt_wav)
        semantic_features = self._extract_semantic(wav_16k)
        style_embedding = self._extract_style(wav_16k)
        reference_mel = self._ref_mel(wav_tgt)
        del wav_16k, wav_tgt

        segments = self.normalizer.segment_text(
            text,
            tokenize_fn=self.tokenizer.tokenize,
            language=lang,
            max_tokens=max_text_tokens_per_segment,
        )
        if not segments:
            segments = [text]

        # Short silence inserted between segments.
        silence_n = int(cross_fade_duration * self.sample_rate) // 3

        for i, seg in enumerate(segments):
            seg_id = f"{request_id or uuid.uuid4().hex}_seg{i}"

            if i > 0 and silence_n > 0:
                yield torch.zeros(1, silence_n, dtype=torch.float32)
            async for chunk in self._synth_segment_stream(
                seg, lang, semantic_features, style_embedding, reference_mel,
                n_timesteps, inference_cfg_rate,
                first_chunk_size_tokens, chunk_size_tokens, overlap_tokens,
                verbose, seg_id=seg_id,
            ):
                yield chunk

        del semantic_features, style_embedding, reference_mel
        torch.cuda.empty_cache()
