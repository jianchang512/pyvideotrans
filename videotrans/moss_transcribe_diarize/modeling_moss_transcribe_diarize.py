"""MossTranscribeDiarizeForConditionalGeneration: Whisper-Medium + VQAdaptor + Qwen3-0.6B.

Architecture:
    log-mel input_features -> HF WhisperEncoder
             -> 4x time merge  (B, T, 1024) -> (B, T/4, 4096)
             -> VQAdaptor       (4096 -> 1024)
             -> masked_scatter into text embeddings
             -> Qwen3-0.6B decoder -> logits
"""

from __future__ import annotations

from typing import Optional

import torch
from torch import nn
from transformers import GenerationMixin, PreTrainedModel
from transformers.modeling_outputs import CausalLMOutputWithPast
from transformers.models.qwen3.modeling_qwen3 import Qwen3Model
from transformers.models.whisper.modeling_whisper import WhisperEncoder
from transformers.utils import torch_compilable_check

from .configuration_moss_transcribe_diarize import MossTranscribeDiarizeConfig


class VQAdaptor(nn.Module):
    """Projects merged Whisper features to LM hidden dim.

    ``Linear(in → hidden) → SiLU → Linear(hidden → hidden) → LayerNorm``
    """

    def __init__(self, input_dim: int, hidden_size: int, norm_eps: float = 1e-6):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_size, bias=True),
            nn.SiLU(),
            nn.Linear(hidden_size, hidden_size, bias=True),
            nn.LayerNorm(hidden_size, eps=norm_eps, bias=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class MossTranscribeDiarizePreTrainedModel(PreTrainedModel):
    config_class = MossTranscribeDiarizeConfig
    base_model_prefix = "model"
    input_modalities = ("audio", "text")
    _no_split_modules = ["Qwen3DecoderLayer", "WhisperEncoderLayer"]
    _skip_keys_device_placement = "past_key_values"
    supports_gradient_checkpointing = True
    _supports_sdpa = True
    _supports_attention_backend = True


class MossTranscribeDiarizeModel(MossTranscribeDiarizePreTrainedModel):
    base_model_prefix = "model"

    """Single-stream multimodal backbone: Whisper-Medium encoder + Qwen3-0.6B.

    Audio features are injected into text embeddings via ``masked_scatter`` at
    positions marked by ``audio_token_id`` in ``input_ids``.
    """

    def __init__(self, config: MossTranscribeDiarizeConfig):
        super().__init__(config)

        self.language_model: nn.Module = Qwen3Model(config.text_config)
        self.whisper_encoder: nn.Module = WhisperEncoder(config.audio_config)
        self.vq_adaptor: VQAdaptor = VQAdaptor(
            input_dim=config.adaptor_input_dim,
            hidden_size=config.text_config.hidden_size,
            norm_eps=config.text_config.rms_norm_eps,
        )
        self.post_init()

    def get_input_embeddings(self):
        return self.language_model.embed_tokens

    def set_input_embeddings(self, value):
        self.language_model.embed_tokens = value

    # ---- 4x time merge ---------------------------------------------------

    def time_merge(self, features: torch.Tensor) -> torch.Tensor:
        """``(B, T, D) -> (B, T//M, D*M)`` where M is ``audio_merge_size``."""
        B, T, D = features.shape
        merge_size = int(self.config.audio_merge_size)
        T_trim = (T // merge_size) * merge_size
        return features[:, :T_trim, :].reshape(B, T_trim // merge_size, D * merge_size)

    # ---- audio feature extraction -----------------------------------------

    def get_audio_features(
        self,
        input_features: torch.Tensor,
        audio_feature_lengths: torch.LongTensor,
        audio_chunk_mapping: Optional[torch.LongTensor] = None,
    ) -> list[torch.Tensor]:
        """Whisper encoder -> 4x time merge -> VQAdaptor.

        Returns list of ``(1, N_tokens, hidden_size)`` tensors.
        """
        if input_features is None:
            raise ValueError("input_features must be provided for audio feature extraction.")
        if audio_feature_lengths is None:
            raise ValueError("audio_feature_lengths must be provided with input_features.")

        device = next(self.whisper_encoder.parameters()).device
        encoder_dtype = next(self.whisper_encoder.parameters()).dtype
        input_features = input_features.to(device=device, dtype=encoder_dtype)
        audio_feature_lengths = audio_feature_lengths.to(device=device)
        if audio_feature_lengths.numel() != input_features.shape[0]:
            raise ValueError(
                "audio_feature_lengths must contain one length per input_features chunk: "
                f"got {audio_feature_lengths.numel()} lengths for {input_features.shape[0]} chunks."
            )

        whisper_features = self.whisper_encoder(input_features, return_dict=True).last_hidden_state

        chunk_mapping = (
            audio_chunk_mapping.to(device=device)
            if audio_chunk_mapping is not None
            else torch.zeros(input_features.shape[0], dtype=torch.long, device=device)
        )
        if chunk_mapping.numel() != input_features.shape[0]:
            raise ValueError(
                "audio_chunk_mapping must contain one sample index per input_features chunk: "
                f"got {chunk_mapping.numel()} indices for {input_features.shape[0]} chunks."
            )

        num_audios = int(chunk_mapping.max().item()) + 1 if chunk_mapping.numel() else 0
        per_audio_chunks = [[] for _ in range(num_audios)]
        for chunk_idx, token_len in enumerate(audio_feature_lengths.tolist()):
            sample_idx = int(chunk_mapping[chunk_idx].item())
            per_audio_chunks[sample_idx].append(
                whisper_features[chunk_idx : chunk_idx + 1, : int(token_len) * 4]
            )

        adapted = []
        for parts in per_audio_chunks:
            feat = torch.cat(parts, dim=1)
            feat = feat.to(self.dtype)
            merged = self.time_merge(feat)
            adapted.append(self.vq_adaptor(merged))
        return adapted

    # ---- inject audio into text embeddings --------------------------------

    def get_placeholder_mask(
        self,
        input_ids: Optional[torch.LongTensor],
        inputs_embeds: torch.FloatTensor,
        audio_features: torch.Tensor,
    ) -> torch.BoolTensor:
        """Return the expanded audio placeholder mask and validate feature count."""
        if input_ids is None:
            special_audio_mask = inputs_embeds == self.get_input_embeddings()(
                torch.tensor(self.config.audio_token_id, dtype=torch.long, device=inputs_embeds.device)
            )
            special_audio_mask = special_audio_mask.all(-1)
        else:
            special_audio_mask = input_ids.to(device=inputs_embeds.device) == self.config.audio_token_id

        if special_audio_mask.shape != inputs_embeds.shape[:2]:
            raise ValueError(
                "input_ids shape must match the first two dimensions of inputs_embeds: "
                f"got {tuple(special_audio_mask.shape)} and {tuple(inputs_embeds.shape[:2])}."
            )

        n_audio_tokens = special_audio_mask.sum()
        special_audio_mask = special_audio_mask.unsqueeze(-1).expand_as(inputs_embeds).to(inputs_embeds.device)
        torch_compilable_check(
            inputs_embeds[special_audio_mask].numel() == audio_features.numel(),
            (
                f"Audio features and audio tokens do not match: "
                f"tokens: {n_audio_tokens}, features {audio_features.shape[0]}"
            ),
        )
        return special_audio_mask

    def inject_audio_features(
        self,
        input_ids,
        inputs_embeds,
        input_features,
        audio_feature_lengths,
        audio_chunk_mapping,
    ):
        """Replace audio placeholder positions with projected audio features."""
        if input_features is None:
            return inputs_embeds
        audio_features = self.get_audio_features(
            input_features=input_features,
            audio_feature_lengths=audio_feature_lengths,
            audio_chunk_mapping=audio_chunk_mapping,
        )
        audio_embeds = torch.cat([f.squeeze(0) for f in audio_features], dim=0)
        audio_embeds = audio_embeds.to(inputs_embeds.device, inputs_embeds.dtype)
        audio_mask = self.get_placeholder_mask(input_ids, inputs_embeds, audio_embeds)
        return inputs_embeds.masked_scatter(audio_mask, audio_embeds)

    # ---- forward ----------------------------------------------------------

    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values=None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        input_features: Optional[torch.FloatTensor] = None,
        audio_feature_lengths: Optional[torch.LongTensor] = None,
        audio_chunk_mapping: Optional[torch.LongTensor] = None,
        **kwargs,
    ):
        return_dict = True if return_dict is None else return_dict
        if input_ids is None and inputs_embeds is None:
            raise ValueError("You must specify one of input_ids or inputs_embeds.")
        if input_ids is not None and inputs_embeds is not None:
            raise ValueError("You must specify only one of input_ids or inputs_embeds.")

        if inputs_embeds is None:
            inputs_embeds = self.get_input_embeddings()(input_ids)
        inputs_embeds = self.inject_audio_features(
            input_ids=input_ids,
            inputs_embeds=inputs_embeds,
            input_features=input_features,
            audio_feature_lengths=audio_feature_lengths,
            audio_chunk_mapping=audio_chunk_mapping,
        )
        if output_attentions is not None:
            kwargs["output_attentions"] = output_attentions
        if output_hidden_states is not None:
            kwargs["output_hidden_states"] = output_hidden_states

        outputs = self.language_model(
            input_ids=None, attention_mask=attention_mask, position_ids=position_ids,
            past_key_values=past_key_values, inputs_embeds=inputs_embeds,
            use_cache=use_cache, **kwargs,
        )
        if not return_dict:
            return outputs.to_tuple()
        return outputs


class MossTranscribeDiarizeForConditionalGeneration(MossTranscribeDiarizePreTrainedModel, GenerationMixin):
    _tied_weights_keys = {"lm_head.weight": "model.language_model.embed_tokens.weight"}

    def __init__(self, config: MossTranscribeDiarizeConfig):
        super().__init__(config)
        self.model = MossTranscribeDiarizeModel(config)
        self.vocab_size = config.text_config.vocab_size
        self.lm_head = nn.Linear(config.text_config.hidden_size, config.text_config.vocab_size, bias=False)
        self.post_init()

    def tie_weights(self, *args, **kwargs):
        result = super().tie_weights(*args, **kwargs)
        if self.model is not None and self.lm_head is not None:
            self.lm_head.weight = self.model.language_model.embed_tokens.weight
        return result

    def get_input_embeddings(self):
        return self.model.get_input_embeddings()

    def set_input_embeddings(self, value):
        self.model.set_input_embeddings(value)

    def get_output_embeddings(self):
        return self.lm_head

    def set_output_embeddings(self, new_embeddings):
        self.lm_head = new_embeddings

    def get_audio_features(
        self,
        input_features: torch.Tensor,
        audio_feature_lengths: torch.LongTensor,
        audio_chunk_mapping: Optional[torch.LongTensor] = None,
    ) -> list[torch.Tensor]:
        return self.model.get_audio_features(
            input_features=input_features,
            audio_feature_lengths=audio_feature_lengths,
            audio_chunk_mapping=audio_chunk_mapping,
        )

    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values=None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        input_features: Optional[torch.FloatTensor] = None,
        audio_feature_lengths: Optional[torch.LongTensor] = None,
        audio_chunk_mapping: Optional[torch.LongTensor] = None,
        logits_to_keep: int | torch.Tensor = 0,
        **kwargs,
    ):
        return_dict = True if return_dict is None else return_dict
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=True,
            input_features=input_features,
            audio_feature_lengths=audio_feature_lengths,
            audio_chunk_mapping=audio_chunk_mapping,
            **kwargs,
        )

        hidden_states = outputs.last_hidden_state
        slice_indices = slice(-logits_to_keep, None) if isinstance(logits_to_keep, int) else logits_to_keep
        logits = self.lm_head(hidden_states[:, slice_indices, :])

        loss = None
        if labels is not None:
            loss = self.loss_function(
                logits=logits,
                labels=labels,
                vocab_size=self.config.text_config.vocab_size,
                **kwargs,
            )

        if not return_dict:
            output = (logits,) + outputs[1:]
            return (loss,) + output if loss is not None else output
        return CausalLMOutputWithPast(
            loss=loss, logits=logits,
            past_key_values=outputs.past_key_values,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

    # ---- generation support -----------------------------------------------

    def prepare_inputs_for_generation(
        self,
        input_ids,
        past_key_values=None,
        attention_mask=None,
        inputs_embeds=None,
        input_features=None,
        audio_feature_lengths=None,
        audio_chunk_mapping=None,
        is_first_iteration=False,
        use_cache=True,
        **kwargs,
    ):
        model_inputs = super().prepare_inputs_for_generation(
            input_ids,
            past_key_values=past_key_values,
            attention_mask=attention_mask, inputs_embeds=inputs_embeds,
            is_first_iteration=is_first_iteration, use_cache=use_cache, **kwargs,
        )
        if input_features is not None and (is_first_iteration or not use_cache):
            model_inputs["input_features"] = input_features
            model_inputs["audio_feature_lengths"] = audio_feature_lengths
            model_inputs["audio_chunk_mapping"] = audio_chunk_mapping
        return model_inputs
