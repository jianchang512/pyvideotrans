import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers4576 import GPT2Config, GPT2Model,DynamicCache
from transformers4576.modeling_utils import PreTrainedModel
from transformers4576.generation import GenerationMixin
from transformers4576.modeling_outputs import CausalLMOutputWithCrossAttentions
from transformers4576.configuration_utils import PretrainedConfig
from dataclasses import dataclass
from typing import Optional, Tuple

from .text_encoder import TextEmbeddingProjector
from .speaker_encoder import Qwen3TTSSpeakerEncoder, Qwen3TTSSpeakerEncoderConfig
from .position_embeddings import DummyPositionEmbedding, LearnedPositionalEmbedding



@dataclass
class Text2SemanticConfig(PretrainedConfig):
    """Configuration for Text2Semantic model.

    Args:
        num_layers: Number of transformer layers
        model_dim: Hidden dimension size
        num_heads: Number of attention heads
        max_text_seq_lens: Maximum text sequence length
        max_semantic_seq_lens: Maximum semantic sequence length
        vocab_size: Size of text vocabulary
        semantic_vocab_size: Size of semantic token vocabulary
        text_embedding_dim: Dimension of input text embeddings
        speaker_embedding_dim: Dimension of speaker/style conditioning vector
        start_semantic_token: BOS token ID for semantic sequence
        stop_semantic_token: EOS token ID for semantic sequence
    """
    model_type = "text2semantic"

    num_layers: int = 24
    #num_hidden_layers: int = 24
    model_dim: int = 1280
    num_heads: int = 20
    max_text_seq_lens: int = 520
    max_semantic_seq_lens: int = 1520
    vocab_size: int = 32000
    semantic_vocab_size: int = 8194
    text_embedding_dim: int = 4096
    speaker_embedding_dim: int = 1024
    start_semantic_token: int = 8192
    stop_semantic_token: int = 8193
    
    # ================= 新增以下代码 =================
    @property
    def num_hidden_layers(self) -> int:
        return self.num_layers

    @num_hidden_layers.setter
    def num_hidden_layers(self, value: int):
        self.num_layers = value
    @property
    def num_attention_heads(self) -> int:
        return self.num_heads
    @property
    def hidden_size(self) -> int:
        return self.model_dim

    def __init__(
        self,
        num_layers: int = 24,
        model_dim: int = 1280,
        num_heads: int = 20,
        max_text_seq_lens: int = 520,
        max_semantic_seq_lens: int = 1520,
        vocab_size: int = 32000,
        semantic_vocab_size: int = 8194,
        text_embedding_dim: int = 4096,
        speaker_embedding_dim: int = 1024,
        start_semantic_token: int = 8192,
        stop_semantic_token: int = 8193,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.num_layers = num_layers
        #self.num_hidden_layers = num_layers
        self.model_dim = model_dim
        self.num_heads = num_heads
        self.max_text_seq_lens = max_text_seq_lens
        self.max_semantic_seq_lens = max_semantic_seq_lens
        self.vocab_size = vocab_size
        self.semantic_vocab_size = semantic_vocab_size
        self.text_embedding_dim = text_embedding_dim
        self.speaker_embedding_dim = speaker_embedding_dim
        self.start_semantic_token = start_semantic_token
        self.stop_semantic_token = stop_semantic_token


class Text2Semantic(PreTrainedModel, GenerationMixin):

    config_class = Text2SemanticConfig

    def __init__(self, config: Text2SemanticConfig):
        super().__init__(config)

        self.config = config
        self.max_seq_len = config.max_text_seq_lens + config.max_semantic_seq_lens + 1

        self.text_projector = TextEmbeddingProjector(
            vocab_size=config.vocab_size,
            embed_dim=config.text_embedding_dim,
            output_size=config.model_dim,
        )

        self.semantic_embedding = nn.Embedding(
            config.semantic_vocab_size, config.model_dim
        )

        self.text_position_embedding = LearnedPositionalEmbedding(
            config.max_text_seq_lens, config.model_dim
        )
        self.semantic_position_embedding = LearnedPositionalEmbedding(
            config.max_semantic_seq_lens, config.model_dim
        )

        gpt_config = GPT2Config(
            vocab_size=config.semantic_vocab_size,
            n_positions=self.max_seq_len,
            n_ctx=self.max_seq_len,
            n_embd=config.model_dim,
            n_layer=config.num_layers,
            n_head=config.num_heads,
            gradient_checkpointing=False,
            use_cache=True,
        )
        self.transformer = GPT2Model(gpt_config)

        # Replace GPT2's position embedding with dummy (we use custom position embeddings)
        del self.transformer.wpe
        self.transformer.wpe = DummyPositionEmbedding(config.model_dim)

        # Remove GPT2's word embedding (we use custom embedding concatenation)
        del self.transformer.wte

        self.final_norm = nn.LayerNorm(config.model_dim)
        self.semantic_head = nn.Linear(config.model_dim, config.semantic_vocab_size)

        speaker_config = Qwen3TTSSpeakerEncoderConfig(
            mel_dim=config.speaker_embedding_dim,
            enc_dim=config.model_dim,
        )
        self.speaker_encoder = Qwen3TTSSpeakerEncoder(speaker_config)

        # Caching for inference efficiency
        self.cached_condition_emb = None
        self.cached_text_emb = None

        self.post_init()


    def _prepare_embed_inputs(
        self,
        text_inputs: Optional[torch.Tensor] = None,
        semantic_codes: Optional[torch.Tensor] = None,
        condition_vector: Optional[torch.Tensor] = None,
        input_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Prepare input embeddings by concatenating condition, text, and semantic embeddings.

        Training mode (text_inputs provided):
            Concatenates all three embedding types with their respective position encodings.

        Inference mode (input_ids provided):
            Uses cached condition and text embeddings, only computes new semantic embeddings.
            Supports both full sequence and single-token (KV-cached) inputs.

        Args:
            text_inputs: Text token IDs, shape (B, T_text)
            semantic_codes: Semantic token IDs, shape (B, T_sem)
            condition_vector: Speaker/style features, shape (B, T_cond, D_spk)
            input_ids: Combined token IDs for inference, shape (B, T) or (B, 1)
            attention_mask: Attention mask for inference, shape (B, T)

        Returns:
            Concatenated embeddings, shape (B, T_total, D)
        """
        if text_inputs is not None:
            # Training mode: full concatenation
            text_emb = self.text_projector(text_inputs)  # (B, T_text, D)
            text_emb = self.text_position_embedding(text_emb)

            semantic_emb = self.semantic_embedding(semantic_codes)  # (B, T_sem, D)
            semantic_emb = self.semantic_position_embedding(semantic_emb)

            condition_emb = self.speaker_encoder(condition_vector).unsqueeze(1)  # (B, 1, D)

            return torch.cat([condition_emb, text_emb, semantic_emb], dim=1)

        else:
            # Inference mode: use cached prefix
            condition_len = self.cached_condition_emb.shape[1]
            text_len = self.cached_text_emb.shape[1]
            prefix_len = condition_len + text_len

            if input_ids.shape[1] != 1:
                # First inference step: full sequence
                semantic_inputs = input_ids[:, prefix_len:]
                semantic_emb = self.semantic_embedding(semantic_inputs)
                semantic_emb = self.semantic_position_embedding(semantic_emb)

                # Handle beam search batch expansion
                repeat_factor = semantic_emb.shape[0] // self.cached_condition_emb.shape[0]
                condition_emb = self.cached_condition_emb.repeat_interleave(repeat_factor, 0)
                text_emb = self.cached_text_emb.repeat_interleave(repeat_factor, 0)

                return torch.cat([condition_emb, text_emb, semantic_emb], dim=1)

            else:
                # KV-cached step: single token
                semantic_emb = self.semantic_embedding(input_ids)  # (B, 1, D)

                # Compute position for this single token
                semantic_pos = attention_mask.shape[1] - prefix_len - 1
                pos_emb = self.semantic_position_embedding.get_fixed_embedding(
                    semantic_pos, input_ids.device
                )
                return semantic_emb + pos_emb

    def forward(
        self,
        input_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        past_key_values: Optional[Tuple] = None,
        inputs_embeds: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        text_inputs: Optional[torch.Tensor] = None,
        text_lengths: Optional[torch.Tensor] = None,
        semantic_codes: Optional[torch.Tensor] = None,
        semantic_lengths: Optional[torch.Tensor] = None,
        condition_vector: Optional[torch.Tensor] = None,
        return_latent: bool = False,
    ):
        """Forward pass for T2S model.

        Training mode (text_inputs provided):
            Computes loss for semantic token prediction given text and condition.

        Inference mode (input_ids provided):
            Generates logits for next semantic token, uses cached KV and embeddings.

        Args:
            input_ids: Token IDs for inference mode
            attention_mask: Attention mask, shape (B, T)
            past_key_values: Cached key/value states from previous steps
            labels: Target semantic tokens for loss computation, shape (B, T_sem)
            text_inputs: Text token IDs, shape (B, T_text)
            text_lengths: Valid text lengths for each batch element, shape (B,)
            semantic_codes: Semantic token IDs with BOS/EOS, shape (B, T_sem)
            semantic_lengths: Valid semantic lengths (excluding BOS/EOS), shape (B,)
            condition_vector: Speaker/style features, shape (B, T_cond, D_spk)
            return_latent: If True, return hidden states instead of logits

        Returns:
            CausalLMOutputWithCrossAttentions with loss, logits, and hidden states
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if text_inputs is not None:
            # Training mode
            inputs_embeds = self._prepare_embed_inputs(
                text_inputs=text_inputs,
                semantic_codes=semantic_codes,
                condition_vector=condition_vector,
            )

            if attention_mask is None:
                # Auto-generate attention mask from lengths
                batch_size = text_inputs.shape[0]
                device = text_inputs.device
                cond_mask = torch.ones(batch_size, 1, dtype=torch.bool, device=device)
                text_mask = torch.arange(text_inputs.shape[1], device=device).unsqueeze(0) < text_lengths.unsqueeze(1)
                semantic_mask = torch.arange(semantic_codes.shape[1], device=device).unsqueeze(0) < (semantic_lengths + 2).unsqueeze(1)
                attention_mask = torch.cat([cond_mask, text_mask, semantic_mask], dim=1)

        else:
            # Inference mode
            inputs_embeds = self._prepare_embed_inputs(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )

        transformer_outputs = self.transformer(
            inputs_embeds=inputs_embeds,
            #past_key_values=past_key_values,
            past_key_values=past_key_values,
            attention_mask=attention_mask,
            position_ids=position_ids,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        hidden_states = transformer_outputs.last_hidden_state  # (B, T_total, D)

        if return_latent:
            # Return latent representations (excluding condition and text prefix, and BOS/EOS)
            return hidden_states[:, 1 + text_inputs.shape[1]:-2]

        if text_inputs is not None:
            # Training: extract semantic portion (skip condition token, then skip text)
            hidden_states = self.final_norm(hidden_states[:, 1:])[:, text_inputs.shape[1]:]

        else:
            # Inference
            hidden_states = self.final_norm(hidden_states)

        logits = self.semantic_head(hidden_states)  # (B, T_sem, vocab_size)

        loss = None
        if labels is not None:
            logits_for_loss = logits.permute(0, 2, 1)  # (B, vocab_size, T_sem)
            loss = F.cross_entropy(logits_for_loss, labels, ignore_index=-100)

        if not return_dict:
            output = (logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return CausalLMOutputWithCrossAttentions(
            loss=loss,
            logits=logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
        )

    def store_conditioning(
        self,
        condition_vector: torch.Tensor,
        text_inputs: torch.Tensor
    ):
        """Cache condition and text embeddings for efficient inference.

        Avoids recomputing prefix embeddings during autoregressive generation.

        Args:
            condition_vector: Speaker/style features, shape (B, T_cond, D_spk)
            text_inputs: Text token IDs, shape (B, T_text)
        """
        with torch.no_grad():
            condition_emb = self.speaker_encoder(condition_vector).unsqueeze(1)
            text_emb = self.text_projector(text_inputs)
            text_emb = self.text_position_embedding(text_emb)

            self.cached_condition_emb = condition_emb
            self.cached_text_emb = text_emb

    def prepare_inputs_for_generation(
        self,
        input_ids,
        past_key_values=None,
        **kwargs
    ):
        """Prepare inputs for HuggingFace generation interface."""
        attention_mask = kwargs.get("attention_mask", None)

        # ================= 修改开始 =================
        # 安全地获取当前 KV Cache 中实际缓存的 token 数量
        past_length = 0
        if past_key_values is not None:
            if hasattr(past_key_values, "get_seq_length"):
                # 适配 Transformers 4.36+ 的新版 Cache 对象 (如 DynamicCache)
                past_length = past_key_values.get_seq_length()
            elif isinstance(past_key_values, tuple) and len(past_key_values) > 0:
                # 兼容旧版本的 Tuple 缓存
                past_length = past_key_values[0][0].shape[-2]

        # 只有当缓存中真的有内容时（第二步及以后），才进行切片操作
        if past_length > 0:
            # Use only last token when KV cache is available
            input_ids = input_ids[:, -1:]
        # ================= 修改结束 =================

        return {
            "input_ids": input_ids,
            "past_key_values": past_key_values,
            "use_cache": kwargs.get("use_cache", True),
            "attention_mask": attention_mask,
        }

    @staticmethod
    def _reorder_cache(past_key_values, beam_idx):
        """Reorder cached KV states for beam search."""
        # ================= 新增兼容逻辑 =================
        # 如果新版 transformers 传入的是 Cache 对象（如 DynamicCache）
        # 则直接调用其自带的 reorder_cache 方法即可
        if hasattr(past_key_values, "reorder_cache"):
            past_key_values.reorder_cache(beam_idx)
            return past_key_values
        # ===============================================

        # 兼容旧版本 tuple 的处理逻辑
        return tuple(
            tuple(
                past_state.index_select(0, beam_idx.to(past_state.device))
                for past_state in layer_past
            )
            for layer_past in past_key_values
        )

    @torch.no_grad()
    def generate(
        self,
        text_inputs: torch.Tensor,
        condition_vector: torch.Tensor,
        max_length: int = 500,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.9,
        do_sample: bool = True,
        eos_token_id: Optional[int] = None,
        return_latent: bool = False,
        **kwargs
    ):
        """Generate semantic tokens from text and condition autoregressively.

        Args:
            text_inputs: Text token IDs, shape (B, T_text)
            condition_vector: Speaker/style features, shape (B, T_cond, D_spk)
            max_length: Maximum total sequence length (prefix + generated tokens)
            temperature: Sampling temperature (higher = more diverse)
            top_k: Top-k sampling parameter
            top_p: Nucleus sampling probability threshold
            do_sample: Use sampling if True, greedy decoding if False
            eos_token_id: Stop token ID (defaults to config.stop_semantic_token)
            return_latent: If True, also return hidden state representations
            **kwargs: Additional generation arguments (num_beams, etc.)

        Returns:
            If return_latent=False: Semantic token IDs, shape (B, T_gen)
            If return_latent=True: Dict with "semantic_codes" and "latent" (hidden states)
        """
        self.store_conditioning(condition_vector, text_inputs)

        batch_size = text_inputs.shape[0]
        device = text_inputs.device
        prefix_len = 1 + text_inputs.shape[1]  # condition(1) + text

        bos = self.config.start_semantic_token
        eos = eos_token_id if eos_token_id is not None else self.config.stop_semantic_token

        # Initialize with BOS tokens for the semantic portion
        start_tokens = torch.full(
            (batch_size, prefix_len + 1),
            fill_value=bos,
            dtype=torch.long,
            device=device,
        )
        attention_mask = torch.ones(batch_size, prefix_len + 1, dtype=torch.long, device=device)

        # Call HuggingFace generate
        generated = super().generate(
            start_tokens,
            attention_mask=attention_mask,
            max_length=max_length,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            do_sample=do_sample,
            eos_token_id=eos,
            pad_token_id=self.config.stop_semantic_token,
            **kwargs
        )

        # Extract semantic tokens (remove prefix and BOS)
        semantic_codes = generated[:, prefix_len + 1:]

        if return_latent:
            # Compute latent representations by forward pass
            with torch.no_grad():
                bos_col = torch.full(
                    (batch_size, 1), bos, dtype=semantic_codes.dtype, device=device,
                )
                semantic_codes = torch.cat([bos_col, semantic_codes], dim=1)
                inputs_embeds = self._prepare_embed_inputs(
                    text_inputs=text_inputs,
                    semantic_codes=semantic_codes,
                    condition_vector=condition_vector,
                )
                text_lengths = torch.tensor([text_inputs.shape[1]], device=device)
                semantic_lengths = torch.tensor([semantic_codes.shape[1] - 2], device=device)

                cond_mask = torch.ones(batch_size, 1, dtype=torch.bool, device=device)
                text_mask = torch.arange(text_inputs.shape[1], device=device).unsqueeze(0) < text_lengths.unsqueeze(1)
                semantic_mask = torch.arange(semantic_codes.shape[1], device=device).unsqueeze(0) < (semantic_lengths + 2).unsqueeze(1)
                attention_mask = torch.cat([cond_mask, text_mask, semantic_mask], dim=1)

                transformer_outputs = self.transformer(
                    inputs_embeds=inputs_embeds,
                    attention_mask=attention_mask,
                    use_cache=False,
                    return_dict=True,
                )

                hidden_states = transformer_outputs.last_hidden_state
                latent = hidden_states[:, 1 + text_inputs.shape[1]:-2]  # Extract semantic portion
                semantic_codes = semantic_codes[:, 1:-1]  # Remove BOS/EOS

            return {
                "semantic_codes": semantic_codes,
                "latent": latent
            }

        return semantic_codes


if __name__ == "__main__":
    print("Testing Text2Semantic...")

    config = Text2SemanticConfig(
        num_layers=2,
        model_dim=128,
        num_heads=2,
    )
    model = Text2Semantic(config)

    print("\n=== Training Mode ===")
    batch_size = 2
    text_inputs = torch.randint(0, config.vocab_size, (batch_size, 10))
    text_lengths = torch.tensor([10, 8])
    semantic_codes = torch.randint(0, config.semantic_vocab_size, (batch_size, 20))
    semantic_targets = torch.randint(0, config.semantic_vocab_size, (batch_size, 20))
    semantic_lengths = torch.tensor([20, 18])
    condition_vector = torch.randn(batch_size, 20, config.speaker_embedding_dim)

    print("\nTest 1: Auto-generated attention_mask")
    outputs = model(
        text_inputs=text_inputs,
        text_lengths=text_lengths,
        semantic_codes=semantic_codes,
        labels=semantic_targets,
        semantic_lengths=semantic_lengths,
        condition_vector=condition_vector,
    )
    print(f"Loss: {outputs.loss.item():.4f}")
    print(f"Logits shape: {outputs.logits.shape}")

    print("\nTest 2: Custom attention_mask")
    custom_attention_mask = torch.ones(batch_size, 1 + 10 + 20, dtype=torch.bool)
    custom_attention_mask[0, 15:] = False
    custom_attention_mask[1, 20:] = False

    outputs = model(
        text_inputs=text_inputs,
        attention_mask=custom_attention_mask,
        semantic_codes=semantic_codes,
        labels=semantic_targets,
        condition_vector=condition_vector,
    )
    print(f"Loss: {outputs.loss.item():.4f}")
    print(f"Logits shape: {outputs.logits.shape}")

    print("\n=== Inference Mode ===")
    model.eval()

    semantic_tokens = model.generate(
        text_inputs=text_inputs[:1],
        condition_vector=condition_vector[:1],
        max_length=20,
        do_sample=False,
    )
    print(f"Generated shape: {semantic_tokens.shape}")
    print(f"Generated tokens: {semantic_tokens[0]}")

    print("\n✓ All tests passed!")
