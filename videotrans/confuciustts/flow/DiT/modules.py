from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization.

    More efficient alternative to LayerNorm without mean centering.

    Args:
        dim: Input dimension
        eps: Small epsilon for numerical stability
    """
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """Compute RMS normalization."""
        return x * torch.rsqrt(torch.mean(x * x, dim=-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply RMS normalization with learnable scale.

        Args:
            x: Input tensor, shape (..., dim)

        Returns:
            Normalized tensor, shape (..., dim)
        """
        output = self._norm(x.float()).type_as(x)
        return output * self.weight


class AdaptiveLayerNorm(nn.Module):
    """Adaptive Layer Normalization conditioned on timestep embedding.

    Applies RMSNorm then modulates with learned scale and shift from conditioning.

    Args:
        hidden_size: Hidden dimension
        eps: Epsilon for normalization
    """

    def __init__(self, hidden_size: int, eps: float = 1e-5):
        super().__init__()
        self.norm = RMSNorm(hidden_size, eps=eps)
        self.modulation = nn.Linear(hidden_size, 2 * hidden_size)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """Apply adaptive normalization.

        Args:
            x: Input tensor, shape (B, T, hidden_size)
            cond: Conditioning vector (timestep embedding), shape (B, hidden_size)

        Returns:
            Modulated tensor, shape (B, T, hidden_size)
        """
        weight, bias = torch.split(self.modulation(cond), self.norm.weight.shape[0], dim=-1)
        return self.norm(x) * weight.unsqueeze(1) + bias.unsqueeze(1)


class FeedForward(nn.Module):
    """SwiGLU feedforward network.

    Uses gated linear units with SiLU activation for improved expressiveness.

    Args:
        dim: Input/output dimension
        intermediate_size: Hidden layer dimension
    """

    def __init__(self, dim: int, intermediate_size: int):
        super().__init__()
        self.w1 = nn.Linear(dim, intermediate_size, bias=False)
        self.w2 = nn.Linear(intermediate_size, dim, bias=False)
        self.w3 = nn.Linear(dim, intermediate_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply SwiGLU: (SiLU(W1(x)) * W3(x)) @ W2.

        Args:
            x: Input tensor, shape (..., dim)

        Returns:
            Output tensor, shape (..., dim)
        """
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


def precompute_freqs_cis(seq_len: int, n_elem: int, base: int = 10000, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    """Precompute rotary position embedding frequencies.

    Args:
        seq_len: Maximum sequence length
        n_elem: Dimension per head
        base: Base for frequency computation
        dtype: Output data type

    Returns:
        Precomputed frequencies, shape (seq_len, n_elem // 2, 2)
    """
    freqs = 1.0 / (base ** (torch.arange(0, n_elem, 2)[: (n_elem // 2)].float() / n_elem))
    t = torch.arange(seq_len, device=freqs.device)
    freqs = torch.outer(t, freqs)
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)
    cache = torch.stack([freqs_cis.real, freqs_cis.imag], dim=-1)
    return cache.to(dtype=dtype)


def apply_rotary_emb(x: torch.Tensor, freqs_cis: torch.Tensor) -> torch.Tensor:
    """Apply rotary position embeddings to query/key tensors.

    Args:
        x: Input tensor, shape (B, T, num_heads, head_dim)
        freqs_cis: Precomputed frequencies, shape (T, head_dim // 2, 2)

    Returns:
        Tensor with rotary embeddings applied, shape (B, T, num_heads, head_dim)
    """
    xshaped = x.float().reshape(*x.shape[:-1], -1, 2)
    freqs_cis = freqs_cis.view(1, xshaped.size(1), 1, xshaped.size(3), 2)
    x_out2 = torch.stack(
        [
            xshaped[..., 0] * freqs_cis[..., 0] - xshaped[..., 1] * freqs_cis[..., 1],
            xshaped[..., 1] * freqs_cis[..., 0] + xshaped[..., 0] * freqs_cis[..., 1],
        ],
        -1,
    )
    x_out2 = x_out2.flatten(3)
    return x_out2.type_as(x)


class Attention(nn.Module):
    """Multi-head self-attention with rotary position embeddings.

    Args:
        dim: Input dimension
        num_heads: Number of attention heads
    """

    def __init__(self, dim: int, num_heads: int):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.wqkv = nn.Linear(dim, dim * 3, bias=False)
        self.wo = nn.Linear(dim, dim, bias=False)

    def forward(self, x: torch.Tensor, attn_mask: torch.Tensor, freqs_cis: torch.Tensor) -> torch.Tensor:
        """Multi-head self-attention with rotary embeddings.

        Args:
            x: Input tensor, shape (B, T, dim)
            attn_mask: Attention mask, shape (B, 1, 1, T)
            freqs_cis: Rotary frequencies, shape (T, head_dim // 2, 2)

        Returns:
            Attention output, shape (B, T, dim)
        """
        bsz, seqlen, dim = x.shape
        q, k, v = self.wqkv(x).chunk(3, dim=-1)

        q = q.view(bsz, seqlen, self.num_heads, self.head_dim)
        k = k.view(bsz, seqlen, self.num_heads, self.head_dim)
        v = v.view(bsz, seqlen, self.num_heads, self.head_dim)

        # Apply rotary position embeddings to Q and K
        q = apply_rotary_emb(q, freqs_cis)
        k = apply_rotary_emb(k, freqs_cis)

        q = q.transpose(1, 2)  # (B, num_heads, T, head_dim)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        y = F.scaled_dot_product_attention(q, k, v, attn_mask=attn_mask, dropout_p=0.0)
        y = y.transpose(1, 2).contiguous().view(bsz, seqlen, dim)
        return self.wo(y)


class DiTBlock(nn.Module):
    """DiT transformer block with adaptive normalization and optional skip connections.

    Args:
        dim: Hidden dimension
        num_heads: Number of attention heads
        intermediate_size: Feedforward intermediate dimension
    """

    def __init__(self, dim: int, num_heads: int, intermediate_size: int):
        super().__init__()
        self.attention = Attention(dim, num_heads)
        self.feed_forward = FeedForward(dim, intermediate_size)
        self.attention_norm = AdaptiveLayerNorm(dim)
        self.ffn_norm = AdaptiveLayerNorm(dim)
        self.skip_in_linear = nn.Linear(dim * 2, dim)

    def forward(
        self,
        x: torch.Tensor,
        cond: torch.Tensor,
        attn_mask: torch.Tensor,
        freqs_cis: torch.Tensor,
        skip_in_x: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """DiT block forward with adaptive norm and optional skip connection.

        Args:
            x: Input tensor, shape (B, T, dim)
            cond: Timestep conditioning, shape (B, dim)
            attn_mask: Attention mask, shape (B, 1, 1, T)
            freqs_cis: Rotary frequencies, shape (T, head_dim // 2, 2)
            skip_in_x: Optional U-Net skip input, shape (B, T, dim)

        Returns:
            Output tensor, shape (B, T, dim)
        """
        if skip_in_x is not None:
            x = self.skip_in_linear(torch.cat([x, skip_in_x], dim=-1))
        h = x + self.attention(self.attention_norm(x, cond), attn_mask, freqs_cis)
        return h + self.feed_forward(self.ffn_norm(h, cond))


class FinalLayer(nn.Module):
    """Final output layer with adaptive normalization.

    Args:
        hidden_size: Hidden dimension
    """
    def __init__(self, hidden_size: int):
        super().__init__()
        self.norm_final = nn.LayerNorm(hidden_size, elementwise_affine=False, eps=1e-6)
        self.linear = nn.Linear(hidden_size, hidden_size, bias=True)
        self.adaLN_modulation = nn.Sequential(
            nn.SiLU(),
            nn.Linear(hidden_size, 2 * hidden_size, bias=True),
        )

    def forward(self, x: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        """Apply adaptive normalization and final projection.

        Args:
            x: Input tensor, shape (B, T, hidden_size)
            c: Conditioning vector (timestep embedding), shape (B, hidden_size)

        Returns:
            Output tensor, shape (B, T, hidden_size)
        """
        shift, scale = self.adaLN_modulation(c).chunk(2, dim=1)
        x = self.norm_final(x) * (1.0 + scale.unsqueeze(1)) + shift.unsqueeze(1)
        return self.linear(x)


class SinusPositionEmbedding(nn.Module):
    """Sinusoidal position embedding for timestep encoding.

    Args:
        dim: Embedding dimension
    """
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x, scale=1000):
        """Generate sinusoidal embeddings.

        Args:
            x: Input timestamps, shape (B,)
            scale: Scaling factor for frequencies

        Returns:
            Position embeddings, shape (B, dim)
        """
        device = x.device
        half_dim = self.dim // 2
        emb = math.log(10000) / half_dim
        emb = torch.exp(torch.arange(half_dim, device=device).float() * -emb)
        emb = scale * x.unsqueeze(1) * emb.unsqueeze(0)
        emb = torch.cat((emb.cos(), emb.sin()), dim=-1)
        return emb


class TimestepEmbedding(nn.Module):
    """Timestep embedding with sinusoidal encoding and MLP projection.

    Args:
        dim: Output embedding dimension
        freq_embed_dim: Frequency embedding dimension
    """
    def __init__(self, dim, freq_embed_dim=256):
        super().__init__()
        self.time_embed = SinusPositionEmbedding(freq_embed_dim)
        self.time_mlp = nn.Sequential(nn.Linear(freq_embed_dim, dim), nn.SiLU(), nn.Linear(dim, dim))

    def forward(self, timestep: float["b"]):  # noqa: F821
        """Embed diffusion timestep.

        Args:
            timestep: Diffusion time, shape (B,)

        Returns:
            Timestep embedding, shape (B, dim)
        """
        time_hidden = self.time_embed(timestep)
        time_hidden = time_hidden.to(timestep.dtype)
        time = self.time_mlp(time_hidden)  # (B, dim)
        return time
