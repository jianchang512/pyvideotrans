"""vLLM adapter for the Text2Semantic (T2S) model.

Defines ``Text2SemanticVLLM``, a vLLM-servable reimplementation of the T2S
transformer, together with the multimodal plumbing needed to feed precomputed
prefix embeddings into the engine.

Because vLLM decodes from token ids but the T2S prefix (speaker + text + BOS) is
best expressed as embeddings, we register the prefix as a "multimodal" audio
input: a single placeholder token ("!") in the prompt is expanded to one slot
per prefix embedding, and those embeddings are merged in before the transformer
runs. Registering this module (via ``patch_vllm``) makes the architecture
available under the name "Text2SemanticVLLM".
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

import torch
from torch import nn
from transformers import BatchFeature

from vllm.compilation.decorators import support_torch_compile
from vllm.config import CacheConfig, VllmConfig
from vllm.config.multimodal import BaseDummyOptions
from vllm.distributed.parallel_state import get_pp_group
from vllm.model_executor.layers.logits_processor import LogitsProcessor
from vllm.model_executor.layers.vocab_parallel_embedding import ParallelLMHead
from vllm.model_executor.model_loader.weight_utils import default_weight_loader
from vllm.sequence import IntermediateTensors
from vllm.model_executor.models.interfaces import SupportsPP
from vllm.model_executor.models.utils import (
    is_pp_missing_parameter,
    make_empty_intermediate_tensors_factory,
    make_layers,
    maybe_prefix,
    _merge_multimodal_embeddings,
)
from vllm.model_executor.models.gpt2 import GPT2Block
from vllm.model_executor.models.interfaces import SupportsMultiModal, MultiModalEmbeddings
from vllm.multimodal import MULTIMODAL_REGISTRY, ModalityData
from vllm.multimodal.inputs import MultiModalFieldConfig, MultiModalKwargsItems
from vllm.multimodal.processing import (
    BaseMultiModalProcessor,
    PromptReplacement,
    BaseProcessingInfo,
    PromptUpdateDetails,
    PromptUpdate,
)
from vllm.multimodal.processing import BaseDummyInputsBuilder
from vllm.multimodal.parse import (
    AudioItem,
    MultiModalDataParser,
    DictEmbeddingItems,
    ModalityDataItems,
    MultiModalDataItems,
)

from .position_embeddings import LearnedPositionalEmbedding

# Placeholder token that stands in for each prefix embedding slot in the prompt.
PLACEHOLDER_TOKEN = "!"
PLACEHOLDER_TOKEN_ID = 0


class ConfuciusTTSProcessingInfo(BaseProcessingInfo):
    """Declares the multimodal capabilities of the T2S model to vLLM."""

    def get_supported_mm_limits(self) -> Mapping[str, Optional[int]]:
        # Unlimited number of "audio" (prefix-embedding) items per request.
        return {"audio": None}

    def get_data_parser(self) -> MultiModalDataParser:
        return ConfuciusTTSDataParser()


class ConfuciusTTSDummyInputsBuilder(BaseDummyInputsBuilder[ConfuciusTTSProcessingInfo]):
    """Builds dummy inputs used by vLLM for profiling / warmup."""

    def get_dummy_text(self, mm_counts: Mapping[str, int]) -> str:
        return PLACEHOLDER_TOKEN * mm_counts.get("audio", 0)

    def get_dummy_mm_data(
        self,
        seq_len: int,
        mm_counts: Mapping[str, int],
        mm_options: Mapping[str, BaseDummyOptions] | None = None,
    ) -> Dict[str, Any]:
        num_items = mm_counts.get("audio", 0)
        if num_items == 0:
            return {}
        # Fabricate prefix embeddings of a representative length for profiling.
        config = self.info.get_hf_config()
        dummy_embed = torch.rand((1024, config.n_embd), dtype=torch.float16)
        return {"audio": {"audio_embeds": [dummy_embed] * num_items}}


class ConfuciusTTSDataParser(MultiModalDataParser):
    """Parses the ``audio_embeds`` payload into vLLM's multimodal item format."""

    def _parse_audio_data(
        self,
        data: ModalityData[AudioItem],
    ) -> ModalityDataItems[Any, Any] | None:
        # We only accept a dict carrying precomputed "audio_embeds".
        if isinstance(data, dict):
            return DictEmbeddingItems(
                data,
                modality="audio",
                required_fields={"audio_embeds"},
                fields_factory=lambda hf_inputs: dict(
                    audio_embeds=MultiModalFieldConfig.batched("audio")
                ),
            )
        raise TypeError(
            f"For 'audio' modality, expected dict with 'audio_embeds', got {type(data)}"
        )


class ConfuciusTTSMultiModalProcessor(BaseMultiModalProcessor[ConfuciusTTSProcessingInfo]):
    """Turns the placeholder prompt + prefix embeds into vLLM model inputs."""

    def _call_hf_processor(
        self,
        prompt: str,
        mm_data: Mapping[str, object],
        mm_kwargs: Mapping[str, object],
        tok_kwargs: Mapping[str, object],
    ) -> BatchFeature:
        # The prompt is just placeholder tokens; tokenize without special tokens.
        tokenizer = self.info.get_tokenizer()
        token_ids = tokenizer.encode(prompt, add_special_tokens=False)
        return BatchFeature(
            data={"input_ids": torch.tensor([token_ids])},
            tensor_type="pt",
        )

    def _get_mm_fields_config(
        self,
        hf_inputs: BatchFeature,
        hf_processor_mm_kwargs: Mapping[str, object],
    ) -> Mapping[str, MultiModalFieldConfig]:
        return dict(audio_embeds=MultiModalFieldConfig.batched("audio"))

    def _get_prompt_updates(
        self,
        mm_items: "MultiModalDataItems",
        hf_processor_mm_kwargs: Mapping[str, object],
        out_mm_kwargs: MultiModalKwargsItems,
    ) -> List[PromptUpdate]:
        out_mm_data = out_mm_kwargs.get_data()

        def get_replacement(item_idx: int):
            # Expand the single "!" placeholder into one slot per prefix embedding
            # so each embedding gets a position in the sequence.
            embeds = out_mm_data["audio_embeds"][item_idx]
            num_features = embeds.shape[0]
            return PromptUpdateDetails.select_token_id(
                [PLACEHOLDER_TOKEN_ID] * num_features, PLACEHOLDER_TOKEN_ID
            )

        return [
            PromptReplacement(
                modality="audio",
                target=PLACEHOLDER_TOKEN,
                replacement=get_replacement,
            )
        ]


@support_torch_compile
class _TransformerBackbone(nn.Module):
    """The stack of GPT2 blocks (plus final layer norm) of the T2S model.

    Wraps vLLM's ``GPT2Block`` layers so the backbone participates in vLLM's
    paged-attention / pipeline-parallel machinery. Embeddings and positional
    encoding are handled by the outer ``Text2SemanticVLLM``.
    """

    def __init__(self, *, vllm_config: VllmConfig, prefix: str = ""):
        super().__init__()
        config = vllm_config.model_config.hf_config
        cache_config = vllm_config.cache_config
        quant_config = vllm_config.quant_config
        self.embed_dim = config.n_embd
        self.start_layer, self.end_layer, self.h = make_layers(
            config.n_layer,
            lambda prefix: GPT2Block(config, cache_config, quant_config, prefix=prefix),
            prefix=f"{prefix}.h",
        )
        self.ln_f = nn.LayerNorm(self.embed_dim, eps=config.layer_norm_epsilon)
        self.make_empty_intermediate_tensors = make_empty_intermediate_tensors_factory(
            ["hidden_states"], config.n_embd
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        position_ids: torch.Tensor,
        intermediate_tensors: Optional[IntermediateTensors],
        inputs_embeds: Optional[torch.Tensor],
    ) -> Union[torch.Tensor, IntermediateTensors]:
        hidden_states = inputs_embeds
        for layer in self.h[self.start_layer:self.end_layer]:
            hidden_states = layer(hidden_states)
        if not get_pp_group().is_last_rank:
            return IntermediateTensors({"hidden_states": hidden_states})
        hidden_states = self.ln_f(hidden_states)
        return hidden_states

    def load_weights(self, weights: Iterable[Tuple[str, torch.Tensor]]) -> Set[str]:
        params_dict = dict(self.named_parameters(remove_duplicate=False))
        loaded_params: Set[str] = set()
        for name, loaded_weight in weights:
            # Skip the causal-mask buffers baked into GPT2 checkpoints.
            if ".attn.bias" in name or ".attn.masked_bias" in name:
                continue
            if is_pp_missing_parameter(name, self):
                continue
            param = params_dict[name]
            # GPT2 stores attention/MLP projections as Conv1D (transposed vs the
            # Linear layers vLLM uses), so transpose their weight matrices.
            for conv1d_name in ["c_attn", "c_proj", "c_fc"]:
                if conv1d_name in name and name.endswith(".weight"):
                    loaded_weight = loaded_weight.t()
            weight_loader = getattr(param, "weight_loader", default_weight_loader)
            weight_loader(param, loaded_weight)
            loaded_params.add(name)
        return loaded_params


@MULTIMODAL_REGISTRY.register_processor(
    ConfuciusTTSMultiModalProcessor,
    info=ConfuciusTTSProcessingInfo,
    dummy_inputs=ConfuciusTTSDummyInputsBuilder,
)
class Text2SemanticVLLM(nn.Module, SupportsPP, SupportsMultiModal):
    """vLLM-servable T2S model that decodes semantic tokens from a prefix.

    Combines semantic token/position embeddings, the GPT2 backbone, and an LM
    head. The speaker/text/BOS prefix is injected as multimodal embeddings (see
    ``embed_input_ids``); only the token-id → embedding path lives here, while
    attention runs inside :class:`_TransformerBackbone`.
    """

    def __init__(self, *, vllm_config: VllmConfig, prefix: str = ""):
        super().__init__()
        config = vllm_config.model_config.hf_config
        quant_config = vllm_config.quant_config
        self.config = config

        self.transformer = _TransformerBackbone(
            vllm_config=vllm_config,
            prefix=maybe_prefix(prefix, "transformer"),
        )
        # Learned positional embeddings for the semantic sequence; index 0 is
        # forced to zero to match the training-time convention.
        n_sem_pos = getattr(config, "n_semantic_positions", config.n_positions)
        self.semantic_position_embedding = LearnedPositionalEmbedding(n_sem_pos, config.n_embd)
        with torch.no_grad():
            self.semantic_position_embedding.embedding.weight[0].zero_()

        self.semantic_embedding = nn.Embedding(config.vocab_size, config.n_embd)

        self.final_norm = nn.LayerNorm(config.n_embd, bias=True)

        self.semantic_head = ParallelLMHead(
            config.vocab_size,
            config.n_embd,
            quant_config=quant_config,
            prefix=f"{prefix}.semantic_head",
            bias=True,
        )
        self.logits_processor = LogitsProcessor(config.vocab_size)
        self.make_empty_intermediate_tensors = (
            self.transformer.make_empty_intermediate_tensors
        )

    def get_language_model(self) -> torch.nn.Module:
        return self.transformer

    def embed_multimodal(self, **kwargs: object) -> MultiModalEmbeddings | None:
        """Normalize the incoming prefix embeddings to a list of (T, D) tensors."""
        audio_embeds = kwargs.get("audio_embeds")
        processed = []
        for embed in audio_embeds:
            # Accept either (T, D) or (1, T, D) and squeeze the batch dim.
            if embed.dim() == 3 and embed.shape[0] == 1:
                processed.append(embed.squeeze(0))
            elif embed.dim() == 2:
                processed.append(embed)
            else:
                raise ValueError(
                    f"Expected audio_embeds 2D or 3D with batch=1, got {embed.shape}"
                )
        return processed

    def embed_input_ids(
        self,
        input_ids: torch.Tensor,
        multimodal_embeddings: MultiModalEmbeddings | None = None,
        *,
        is_multimodal: torch.Tensor | None = None,
        handle_oov_mm_token: bool = False,
    ) -> torch.Tensor:
        """Embed token ids, then overwrite placeholder slots with prefix embeds."""
        inputs_embeds = self.semantic_embedding(input_ids)
        if multimodal_embeddings is not None and len(multimodal_embeddings) != 0:
            # Replace embeddings at placeholder positions with the prefix embeds.
            inputs_embeds = _merge_multimodal_embeddings(
                inputs_embeds=inputs_embeds,
                multimodal_embeddings=multimodal_embeddings,
                is_multimodal=(input_ids == PLACEHOLDER_TOKEN_ID),
            )
        return inputs_embeds

    def forward(
        self,
        input_ids: torch.Tensor,
        positions: torch.Tensor,
        intermediate_tensors: Optional[IntermediateTensors] = None,
        inputs_embeds: Optional[torch.Tensor] = None,
        **kwargs,
    ) -> Union[torch.Tensor, IntermediateTensors]:
        """Add semantic positional embeddings and run the transformer backbone.

        ``positions`` are shifted by ``patch_vllm`` so the semantic sequence is
        indexed from 0 regardless of the prefix length; clamp guards the prefix
        region (negative positions) before the lookup.
        """
        positions = torch.clamp(positions, min=0)
        pos_emb = self.semantic_position_embedding.embedding(positions)
        inputs_embeds += pos_emb

        hidden = self.transformer(
            input_ids=None,
            position_ids=positions,
            intermediate_tensors=intermediate_tensors,
            inputs_embeds=inputs_embeds,
        )
        hidden = self.final_norm(hidden)
        return hidden

    def compute_logits(self, hidden_states: torch.Tensor) -> torch.Tensor | None:
        return self.logits_processor(self.semantic_head, hidden_states)

    def load_weights(self, weights: Iterable[Tuple[str, torch.Tensor]]) -> Set[str]:
        # These prefix modules run natively in ConfuciusTTSVLLM (to build the
        # prefix embeds), so their weights are not needed inside the vLLM model.
        _SKIP_PREFIXES = ("text_projector.", "speaker_encoder.", "text_position_embedding.")

        params_dict = dict(self.named_parameters(remove_duplicate=False))
        loaded_params: Set[str] = set()

        for name, loaded_weight in weights:
            if any(name.startswith(p) for p in _SKIP_PREFIXES):
                continue
            # Skip GPT2 causal-mask buffers.
            if ".attn.bias" in name or ".attn.masked_bias" in name:
                continue

            if is_pp_missing_parameter(name, self):
                continue
            if name not in params_dict:
                continue

            param = params_dict[name]
            # Transpose GPT2 Conv1D weights in the backbone (see backbone loader).
            if name.startswith("transformer."):
                for conv1d_name in ["c_attn", "c_proj", "c_fc"]:
                    if conv1d_name in name and name.endswith(".weight"):
                        loaded_weight = loaded_weight.t()
            weight_loader = getattr(param, "weight_loader", default_weight_loader)
            weight_loader(param, loaded_weight)
            loaded_params.add(name)

        # Re-zero position 0 in case it was overwritten during loading.
        with torch.no_grad():
            self.semantic_position_embedding.embedding.weight[0].zero_()

        return loaded_params
