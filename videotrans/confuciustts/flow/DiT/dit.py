from __future__ import annotations

import torch
import torch.nn as nn

from videotrans.confuciustts.flow.wavenet import WN
from videotrans.confuciustts.flow.DiT.modules import (
    TimestepEmbedding,
    DiTBlock,
    AdaptiveLayerNorm,
    FinalLayer,
    precompute_freqs_cis,
)


class InputEmbedding(nn.Module):
    """Input embedding layer combining mel, conditioning, and speaker features.

    Projects and concatenates:
    - Noisy mel-spectrogram
    - Reference mel conditioning
    - Semantic/text conditioning (mu)
    - Speaker style embedding (optional)

    Args:
        mel_dim: Mel-spectrogram dimension
        cond_dim: Conditioning vector dimension
        out_dim: Output embedding dimension
        spk_dim: Speaker embedding dimension (0 to disable)
    """

    def __init__(self, mel_dim: int, cond_dim: int, out_dim: int, spk_dim: int = 0):
        super().__init__()
        self.spk_dim = spk_dim
        self.mu_projection = nn.Linear(cond_dim, out_dim, bias=True)
        self.proj = nn.Linear(out_dim + mel_dim * 2 + spk_dim, out_dim)

    def forward(
        self,
        x: torch.Tensor,
        cond: torch.Tensor,
        mu: torch.Tensor,
        spks: torch.Tensor,
    ) -> torch.Tensor:
        """Combine and project input features.

        Args:
            x: Noisy mel-spectrogram, shape (B, T, mel_dim)
            cond: Reference mel conditioning, shape (B, T, mel_dim)
            mu: Semantic/text conditioning, shape (B, T, cond_dim)
            spks: Speaker embedding, shape (B, spk_dim)

        Returns:
            Combined embeddings, shape (B, T, out_dim)
        """
        mu_proj = self.mu_projection(mu)
        to_cat = [x, cond, mu_proj]
        if self.spk_dim > 0:
            spks_seq = spks.unsqueeze(1).expand(-1, x.shape[1], -1)  # (B, T, spk_dim)
            to_cat.append(spks_seq)
        return self.proj(torch.cat(to_cat, dim=-1))


class DiT(nn.Module):
    """Diffusion Transformer for velocity prediction in flow matching.

    Architecture:
    1. Input embedding (mel + conditioning + speaker)
    2. Timestep embedding for diffusion time
    3. Transformer blocks with rotary position embeddings
    4. Optional U-Net-style skip connections
    5. Final layer (WaveNet or MLP)

    Args:
        hidden_dim: Transformer hidden dimension
        num_heads: Number of attention heads
        depth: Number of transformer blocks
        mel_dim: Mel-spectrogram dimension
        mu_dim: Conditioning vector dimension
        spk_dim: Speaker embedding dimension
        long_skip_connection: Enable U-Net skip connections
        max_seq_len: Maximum sequence length for rotary embeddings
        ff_intermediate_size: Feedforward intermediate size (default: hidden_dim * 4)
        final_layer: "wavenet" or "mlp"
        wavenet_*: WaveNet final layer parameters
    """

    def __init__(
        self,
        hidden_dim: int = 512,
        num_heads: int = 8,
        depth: int = 13,
        mel_dim: int = 80,
        mu_dim: int = 512,
        spk_dim: int = 192,
        long_skip_connection: bool = True,
        max_seq_len: int = 4096,
        ff_intermediate_size: int | None = None,
        final_layer: str = "wavenet",
        wavenet_hidden_dim: int = 512,
        wavenet_kernel_size: int = 5,
        wavenet_dilation_rate: int = 1,
        wavenet_num_layers: int = 8,
        wavenet_dropout: float = 0.0,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.in_channels = mel_dim
        self.mu_dim = mu_dim
        self.spk_dim = spk_dim
        self.final_layer_type = final_layer
        self.depth = depth
        self.max_seq_len = max_seq_len

        # Input projection
        self.input_embed = InputEmbedding(mel_dim, mu_dim, hidden_dim, spk_dim)
        self.t_embedder = TimestepEmbedding(hidden_dim)
        self.skip_linear = nn.Linear(hidden_dim + mel_dim, hidden_dim) if long_skip_connection else None

        # Transformer blocks with U-Net skip connections
        intermediate_size = ff_intermediate_size if ff_intermediate_size is not None else hidden_dim * 4
        self._emit_skip = set(i for i in range(depth) if i < depth // 2) if long_skip_connection else set()
        self._receive_skip = set(i for i in range(depth) if i > depth // 2) if long_skip_connection else set()
        self.transformer_blocks = nn.ModuleList(
            [DiTBlock(hidden_dim, num_heads, intermediate_size) for _ in range(depth)]
        )
        self.transformer_norm = AdaptiveLayerNorm(hidden_dim)

        # Rotary position embeddings
        head_dim = hidden_dim // num_heads
        freqs_cis = precompute_freqs_cis(max_seq_len, head_dim, base=10000, dtype=torch.float32)
        self.register_buffer("freqs_cis", freqs_cis)

        # Final projection layer
        if self.final_layer_type == "wavenet":
            self.t_embedder2 = TimestepEmbedding(wavenet_hidden_dim)
            self.conv1 = nn.Linear(hidden_dim, wavenet_hidden_dim)
            self.wavenet = WN(
                hidden_channels=wavenet_hidden_dim,
                kernel_size=wavenet_kernel_size,
                dilation_rate=wavenet_dilation_rate,
                n_layers=wavenet_num_layers,
                gin_channels=wavenet_hidden_dim,
                p_dropout=wavenet_dropout,
            )
            self.final_layer = FinalLayer(wavenet_hidden_dim)
            self.res_projection = nn.Linear(hidden_dim, wavenet_hidden_dim)
            self.conv2 = nn.Conv1d(wavenet_hidden_dim, mel_dim, 1)
        else:
            self.final_mlp = nn.Linear(hidden_dim, mel_dim)

    def initialize_weights(self):
        """Initialize model weights with Kaiming normal for Linear layers."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.LayerNorm):
                if m.weight is not None:
                    nn.init.constant_(m.weight, 1)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(
        self,
        x: torch.Tensor,
        mask: torch.Tensor,
        mu: torch.Tensor,
        t: torch.Tensor,
        spks: torch.Tensor | None = None,
        cond: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Forward pass predicting velocity field for flow matching.

        Args:
            x: Noisy mel-spectrogram, shape (B, mel_dim, T)
            mask: Padding mask, shape (B, 1, T)
            mu: Semantic/text conditioning, shape (B, T, cond_dim)
            t: Diffusion timestep, shape (B,)
            spks: Speaker embedding, shape (B, spk_dim) or None
            cond: Reference mel conditioning, shape (B, mel_dim, T) or None

        Returns:
            Predicted velocity, shape (B, mel_dim, T)
        """
        if cond is None:
            cond = torch.zeros_like(x)
        if spks is None:
            spks = torch.zeros(x.size(0), self.spk_dim, device=x.device, dtype=x.dtype)

        assert x.dim() == 3, f"Expected 3D tensor, got {x.dim()}D"
        assert x.size(1) == self.in_channels, \
            f"Expected {self.in_channels} channels, got {x.size(1)}"
        assert x.shape == cond.shape, \
            "x and cond must have the same shape"

        # Transpose to (B, T, C) for transformer
        x = x.transpose(1, 2)
        cond = cond.transpose(1, 2)
        bsz, seq_len, _ = x.shape
        t1 = self.t_embedder(t)  # Timestep embedding
        x_in = self.input_embed(x, cond, mu, spks)

        attn_mask = mask.view(bsz, 1, 1, seq_len)

        freqs_cis = self.freqs_cis[:seq_len]

        # Transformer blocks with U-Net skip connections
        skip_stack: list[torch.Tensor] = []
        h = x_in
        for idx, block in enumerate(self.transformer_blocks):
            skip_in = skip_stack.pop(-1) if idx in self._receive_skip and skip_stack else None
            h = block(h, t1, attn_mask, freqs_cis, skip_in)
            if idx in self._emit_skip:
                skip_stack.append(h)
        x_res = self.transformer_norm(h, t1)

        # Long skip connection from input
        if self.skip_linear is not None:
            x_res = self.skip_linear(torch.cat([x_res, x], dim=-1))

        # Final projection layer
        if self.final_layer_type == "wavenet":
            # WaveNet-based final layer
            x_out = self.conv1(x_res).transpose(1, 2)
            t2 = self.t_embedder2(t)
            x_mask = mask.unsqueeze(1).to(x_out.dtype)
            x_out = self.wavenet(x_out, x_mask, g=t2.unsqueeze(2))
            x_out = x_out.transpose(1, 2) + self.res_projection(x_res)
            x_out = self.final_layer(x_out, t1).transpose(1, 2)
            x_out = self.conv2(x_out)
            return x_out

        # MLP-based final layer
        x_out = self.final_mlp(x_res)
        return x_out.transpose(1, 2)
