import argparse
import os
import sys
from typing import Optional

import safetensors.torch
import torch
import torchaudio
import yaml
from transformers4576 import AutoTokenizer, SeamlessM4TFeatureExtractor, Wav2Vec2BertModel
from huggingface_hub import hf_hub_download

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from videotrans.external.bigvgan.bigvgan import BigVGAN
from videotrans.external.campplus import CAMPPlus

from videotrans.confuciustts.flow.flow import MaskedDiffWithXvec, MaskedDiffWithXvecConfig
from videotrans.confuciustts.frontend.text_normalizer import TextNormalizer
from videotrans.confuciustts.llm.llm import Text2Semantic, Text2SemanticConfig
from videotrans.confuciustts.utils.audio_features import mel_spectrogram
from videotrans.confuciustts.utils.audio_post import cross_fade_concat
from videotrans.confuciustts.utils.text_utils import LANGUAGE_TOKEN_MAP
from videotrans.configure.config import ROOT_DIR

class ConfuciusTTS:
    """Zero-shot multilingual TTS system based on a two-stage architecture.

    Workflow:
    1. Load reference audio to extract style and semantic conditioning
    2. Text → Semantic tokens (T2S model, LLM-based)
    3. Semantic tokens → Mel-spectrogram (S2A model, flow matching)
    4. Mel → Waveform (BigVGAN vocoder)

    Args:
        config_path: Path to YAML configuration file with model paths and audio parameters
        t2s_checkpoint: Optional path to T2S checkpoint (overrides config)
        device: Device for inference ("cuda" or "cpu")
    """
    def __init__(
        self,
        config_path: str = "config/inference_config.yaml",
        t2s_checkpoint: Optional[str] = None,
        device: str = "cuda",
    ):
        self.device = torch.device(device)

        self.cfg = {'log_dir': None, 'seed': None, 'paths': {'style_encoder': {'target': 'external.campplus.CAMPPlus', 'init_args': {'feat_dim': 80, 'embedding_size': 192}, 'checkpoint': 'campplus_cn_common.bin'}, 't2s_checkpoint': 't2s_model.safetensors', 's2a_checkpoint': 's2a_model.pt'}, 't2s_model': {'num_layers': 24, 'model_dim': 1280, 'num_heads': 20, 'max_text_seq_lens': 520, 'max_semantic_seq_lens': 1520, 'vocab_size': 32000, 'semantic_vocab_size': 8194, 'text_embedding_dim': 4096, 'speaker_embedding_dim': 1024, 'start_semantic_token': 8192, 'stop_semantic_token': 8193}, 's2a_model': {'input_size': 512, 'output_size': 80, 'spk_embed_dim': 192, 'semantic_embed_dim': 1024, 'lm_latent_dim': 1280, 'estimator_mlp_ratio': 3.0}, 'audio': {'target_sample_rate': 22050, 'prompt_sample_rate': 16000, 'n_fft': 1024, 'hop_length': 256, 'win_length': 1024, 'n_mels': 80, 'fmin': 0, 'fmax': None}}

        
        paths = self.cfg["paths"]
        paths["t2s_checkpoint"] = 't2s_model.safetensors'
        if t2s_checkpoint is not None:
            paths["t2s_checkpoint"] = t2s_checkpoint


        self.sample_rate = self.cfg["audio"]["target_sample_rate"]
        self.n_mels = self.cfg["audio"]["n_mels"]
        self.n_fft = self.cfg["audio"]["n_fft"]
        self.hop_length = self.cfg["audio"]["hop_length"]
        self.win_length = self.cfg["audio"]["win_length"]
        self.fmin = self.cfg["audio"]["fmin"]
        self.fmax = self.cfg["audio"]["fmax"]

        self.normalizer = TextNormalizer()

        self.feature_extractor = SeamlessM4TFeatureExtractor.from_pretrained(f'{ROOT_DIR}/models/models--facebook--w2v-bert-2.0')
        self.w2v_model = Wav2Vec2BertModel.from_pretrained(f'{ROOT_DIR}/models/models--facebook--w2v-bert-2.0').eval().to(self.device)
        stats = torch.load(f'{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS/wav2vec2bert_stats.pt', map_location="cpu")
        self.semantic_mean = stats["mean"].to(self.device)
        self.semantic_std = torch.sqrt(stats["var"]).to(self.device)

        spk_cfg = {"target": "external.campplus.CAMPPlus", "init_args":{ "feat_dim": 80, "embedding_size": 192},"checkpoint": "campplus_cn_common.bin"}
        self.style_encoder = CAMPPlus(**spk_cfg.get("init_args", {}))
        style_encoder_path = f'{ROOT_DIR}/models/models--funasr--campplus/{spk_cfg["checkpoint"]}'
        
        spk_state = torch.load(style_encoder_path, map_location="cpu")
        if isinstance(spk_state, dict) and "state_dict" in spk_state:
            spk_state = spk_state["state_dict"]
        self.style_encoder.load_state_dict(spk_state, strict=False)
        self.style_encoder.eval().to(self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(f'{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS')
        t2s_config = Text2SemanticConfig(**self.cfg["t2s_model"])
        self.t2s_model = Text2Semantic(t2s_config)
        self.t2s_model.config.vocab_size = t2s_config.semantic_vocab_size

        t2s_model_path = f'{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS/{paths["t2s_checkpoint"]}'
        
        self.t2s_model.load_state_dict(
            safetensors.torch.load_file(t2s_model_path, device="cpu")
        )
        self.t2s_model.eval().to(self.device)

        s2a_config = MaskedDiffWithXvecConfig(**self.cfg["s2a_model"])
        self.s2a_model = MaskedDiffWithXvec(s2a_config)
        s2a_model_path = f'{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS/{paths["s2a_checkpoint"]}'
        
        self.s2a_model.load_state_dict(
            torch.load(s2a_model_path, map_location="cpu", weights_only=False)
        )
        self.s2a_model.eval().to(self.device)

        self.bigvgan = BigVGAN.from_pretrained(f'{ROOT_DIR}/models/models--nvidia--bigvgan_v2_22khz_80band_256x', use_cuda_kernel=False)
        self.bigvgan.remove_weight_norm()
        self.bigvgan.eval().to(self.device)

    def _load_prompt(self, prompt_wav: str):
        """Load and resample reference audio to 16kHz and target sample rate.

        Args:
            prompt_wav: Path to reference audio file

        Returns:
            Tuple of (wav_16k, wav_tgt) resampled to 16kHz and target sample rate
        """
        wav, sr = torchaudio.load(prompt_wav)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        wav_16k = wav if sr == 16000 else torchaudio.functional.resample(wav, sr, 16000)
        wav_tgt = wav if sr == self.sample_rate else torchaudio.functional.resample(wav, sr, self.sample_rate)
        return wav_16k, wav_tgt

    def _ref_mel(self, wav_tgt: torch.Tensor) -> torch.Tensor:
        """Extract mel-spectrogram from reference audio for S2A conditioning.

        Args:
            wav_tgt: Waveform at target sample rate, shape (C, T)

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

    def _extract_semantic(self, wav_16k: torch.Tensor) -> torch.Tensor:
        """Extract normalized semantic features from reference audio using Wav2Vec2-BERT.

        Args:
            wav_16k: Waveform at 16kHz, shape (1, T)

        Returns:
            Normalized hidden states from layer 17, shape (1, T_feat, D)
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
        feats = outputs.hidden_states[17]  # Layer 17 hidden states
        return (feats - self.semantic_mean) / self.semantic_std

    def _extract_style(self, wav_16k: torch.Tensor) -> torch.Tensor:
        """Extract speaker style embedding using CAMPPlus encoder.

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
    def _synth_segment(
        self,
        text: str,
        lang: str,
        semantic_features: torch.Tensor,
        style_embedding: torch.Tensor,
        reference_mel: torch.Tensor,
        temperature: float,
        top_p: float,
        top_k: int,
        num_beams: int,
        repetition_penalty: float,
        max_length: int,
        n_timesteps: int,
        inference_cfg_rate: float,
        verbose: bool,
    ) -> torch.Tensor:
        """Synthesize audio for a single text segment using T2S and S2A models.

        Args:
            text: Input text segment
            lang: Language code (e.g., "zh", "en")
            semantic_features: Conditioning features from reference audio, shape (1, T_feat, D)
            style_embedding: Speaker style vector, shape (1, D_style)
            reference_mel: Reference mel-spectrogram, shape (1, T_mel, n_mels)
            temperature: Sampling temperature for T2S generation
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            num_beams: Beam search width
            repetition_penalty: Penalty for repeating tokens
            max_length: Maximum sequence length for T2S generation
            n_timesteps: Number of diffusion steps for S2A
            inference_cfg_rate: Classifier-free guidance rate
            verbose: Print debug info

        Returns:
            Generated waveform, shape (1, T_audio)
        """
        lang_token = LANGUAGE_TOKEN_MAP.get(lang, f"请用{lang}朗读接下来的文字")
        formatted = f"You are a helpful assistant. {lang_token}:{text}"
        token_ids = self.tokenizer.encode(formatted, return_tensors="pt").to(self.device)

        t2s_out = self.t2s_model.generate(
            text_inputs=token_ids,
            condition_vector=semantic_features,
            max_length=max_length,
            num_beams=num_beams,
            do_sample=True,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            early_stopping=True,
            return_latent=True,
        )
        semantic_codes = t2s_out["semantic_codes"]  # (B, T_semantic)
        lm_latent = t2s_out["latent"]  # (B, T_semantic, D_hidden)

        # Predict target mel length (heuristic: 1.72x semantic length)
        T = semantic_codes.shape[1]
        target_lengths = torch.tensor([int(T * 1.72)], device=self.device)

        # S2A: Generate mel-spectrogram from semantic tokens
        mel = self.s2a_model.inference(
            semantic_token=semantic_codes,
            lm_latent=lm_latent,
            prompt_feat=reference_mel,
            embedding=style_embedding,
            target_feat_len=target_lengths,
            n_timesteps=n_timesteps,
            inference_cfg_rate=inference_cfg_rate,
        )
        # Vocoder: Mel → Waveform
        return self.bigvgan(mel.float().to(self.device)).squeeze(1)

    @torch.no_grad()
    def generate(
        self,
        text: str,
        lang: str,
        prompt_wav: str,
        temperature: float = 0.8,
        top_p: float = 0.8,
        top_k: int = 30,
        num_beams: int = 3,
        repetition_penalty: float = 10.0,
        max_length: int = 1520,
        n_timesteps: int = 25,
        inference_cfg_rate: float = 0.7,
        max_text_tokens_per_segment: int = 80,
        cross_fade_duration: float = 0.3,
        edge_fade_duration: float = 0.1,
        edge_pad_duration: float = 0.1,
        verbose: bool = False,
    ) -> torch.Tensor:
        """Generate speech audio from text with voice cloning.

        Performs text normalization, segmentation, then synthesizes each segment
        independently and merges them with cross-fade.

        Args:
            text: Input text to synthesize
            lang: Language code (e.g., "zh", "en", "ja", "ko")
            prompt_wav: Path to reference audio for voice cloning
            temperature: Sampling temperature for T2S (higher = more diverse)
            top_p: Nucleus sampling probability threshold
            top_k: Top-k sampling parameter
            num_beams: Beam search width (1 = greedy)
            repetition_penalty: Penalty for repeating tokens (higher = less repetition)
            max_length: Maximum semantic token sequence length
            n_timesteps: Number of diffusion steps for S2A (more = higher quality, slower)
            inference_cfg_rate: Classifier-free guidance scale (0 = unconditional, higher = stronger guidance)
            max_text_tokens_per_segment: Maximum tokens per segment before splitting
            cross_fade_duration: Cross-fade duration between segments in seconds
            edge_fade_duration: Fade duration at start/end in seconds
            edge_pad_duration: Padding duration at edges in seconds
            verbose: Print processing info

        Returns:
            Generated audio waveform, shape (1, T_audio) at target sample rate
        """
        # Normalize text (punctuation, numbers, etc.)
        text = self.normalizer.normalize(text, language=lang)
        if verbose:
            print(f"[ConfuciusTTS] normalized text: {text}")

        # Extract conditioning from reference audio
        wav_16k, wav_tgt = self._load_prompt(prompt_wav)
        semantic_features = self._extract_semantic(wav_16k)
        style_embedding = self._extract_style(wav_16k)
        reference_mel = self._ref_mel(wav_tgt)

        # Split long text into segments
        segments = self.normalizer.segment_text(
            text,
            tokenize_fn=self.tokenizer.tokenize,
            language=lang,
            max_tokens=max_text_tokens_per_segment,
        )
        if not segments:
            segments = [text]
        if verbose:
            print(f"[ConfuciusTTS] {len(segments)} segment(s)")

        # Synthesize each segment independently
        chunks = []
        for i, seg in enumerate(segments):
            if verbose:
                print(f"[ConfuciusTTS] segment {i + 1}/{len(segments)}: {seg!r}")
            audio = self._synth_segment(
                seg, lang, semantic_features, style_embedding, reference_mel,
                temperature, top_p, top_k, num_beams, repetition_penalty,
                max_length, n_timesteps, inference_cfg_rate, verbose,
            )
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            chunks.append(audio)

        # Merge segments with cross-fade
        merged = cross_fade_concat(chunks, self.sample_rate,
                                   silence_duration=cross_fade_duration)

        return merged



def main():
    """CLI entry point for ConfuciusTTS inference."""
    parser = argparse.ArgumentParser(description="ConfuciusTTS zero-shot inference")
    parser.add_argument("--text", type=str, required=True)
    parser.add_argument("--lang", type=str, default="zh")
    parser.add_argument("--prompt_wav", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--config", type=str, default="config/inference_config.yaml")
    parser.add_argument("--t2s_checkpoint", type=str, default=None)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--cross_fade_duration", type=float, default=0.3)
    parser.add_argument("--edge_fade_duration", type=float, default=0.1)
    parser.add_argument("--edge_pad_duration", type=float, default=0.1)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    model = ConfuciusTTS(
        config_path=args.config,
        t2s_checkpoint=args.t2s_checkpoint,
        device=args.device,
    )
    audio = model.generate(
        args.text, args.lang, args.prompt_wav,
        cross_fade_duration=args.cross_fade_duration,
        edge_fade_duration=args.edge_fade_duration,
        edge_pad_duration=args.edge_pad_duration,
        verbose=args.verbose,
    )
    torchaudio.save(args.output, audio.cpu(), model.sample_rate)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
