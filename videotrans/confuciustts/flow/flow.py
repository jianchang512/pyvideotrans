# Copyright (c) 2024 Alibaba Inc (authors: Xiang Lyu, Zhihao Du)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Dict, Optional
from dataclasses import dataclass

import torch
import torch.nn as nn

from videotrans.confuciustts.utils.mask import make_pad_mask
from videotrans.confuciustts.flow.modules import SemanticTokenEmbedding
from videotrans.confuciustts.flow.length_regulator import InterpolateRegulator
from videotrans.confuciustts.flow.flow_matching import ConditionalCFM


@dataclass
class MaskedDiffWithXvecConfig:
    """Configuration for masked diffusion S2A model.

    Args:
        input_size: Input feature dimension
        output_size: Output mel-spectrogram dimension (n_mels)
        spk_embed_dim: Speaker/style embedding dimension
        semantic_embed_dim: Semantic token embedding dimension
        lm_latent_dim: LLM hidden state dimension from T2S model
        semantic_codebook_size: Number of semantic tokens
        semantic_codebook_dim: Codebook dimension for token embedding
        semantic_output_dim: Output dimension after token embedding
        lr_*: Length regulator parameters for upsampling
        cfm_*: Conditional flow matching parameters
        estimator_*: DiT/WaveNet estimator architecture parameters
    """
    input_size: int = 512
    output_size: int = 80
    spk_embed_dim: int = 192
    semantic_embed_dim: int = 1024
    lm_latent_dim: int = 1280

    semantic_codebook_size: int = 8192
    semantic_codebook_dim: int = 8
    semantic_output_dim: int = 1024

    lr_channels: int = 512
    lr_sampling_ratios: tuple = (1, 1, 1, 1)
    lr_out_channels: int = 512
    lr_groups: int = 1
    lr_in_channels: int = 1024

    cfm_sigma_min: float = 1.0e-6
    cfm_training_cfg_rate: float = 0.2
    cfm_inference_cfg_rate: float = 0.7
    cfm_t_scheduler: str = "linear"

    estimator_hidden_dim: int = 512
    estimator_num_heads: int = 8
    estimator_depth: int = 13
    estimator_mel_dim: int = 80
    estimator_cond_dim: int = 512
    estimator_style_dim: int = 192
    estimator_mlp_ratio: float = 4.0
    estimator_dropout: float = 0.0
    estimator_long_skip_connection: bool = True
    estimator_final_layer: str = "wavenet"
    estimator_wavenet_hidden_dim: int = 512
    estimator_wavenet_kernel_size: int = 5
    estimator_wavenet_dilation_rate: int = 1
    estimator_wavenet_num_layers: int = 8
    estimator_wavenet_dropout: float = 0.0


class MaskedDiffWithXvec(nn.Module):
    """Masked diffusion model for semantic-to-acoustic conversion with style conditioning.

    Architecture:
        1. Embed semantic tokens
        2. Concatenate with LLM latent features
        3. Upsample to mel frame rate via length regulator
        4. Generate mel-spectrogram using conditional flow matching

    Supports prompt-based conditioning during training for robustness.
    """
    def __init__(self, config: MaskedDiffWithXvecConfig):
        super().__init__()

        self.input_size = config.input_size
        self.output_size = config.output_size
        self.spk_embed_dim = config.spk_embed_dim
        self.semantic_embed_dim = config.semantic_embed_dim
        self.lm_latent_dim = config.lm_latent_dim

        self.length_regulator = InterpolateRegulator(
            channels=config.lr_channels,
            sampling_ratios=list(config.lr_sampling_ratios),
            out_channels=config.lr_out_channels,
            groups=config.lr_groups,
            in_channels=config.lr_in_channels,
        )

        self.decoder = ConditionalCFM(
            sigma_min=config.cfm_sigma_min,
            training_cfg_rate=config.cfm_training_cfg_rate,
            inference_cfg_rate=config.cfm_inference_cfg_rate,
            t_scheduler=config.cfm_t_scheduler,
            hidden_dim=config.estimator_hidden_dim,
            num_heads=config.estimator_num_heads,
            depth=config.estimator_depth,
            mel_dim=config.estimator_mel_dim,
            cond_dim=config.estimator_cond_dim,
            style_dim=config.estimator_style_dim,
            long_skip_connection=config.estimator_long_skip_connection,
            ff_intermediate_size=int(config.estimator_hidden_dim * config.estimator_mlp_ratio) if config.estimator_mlp_ratio else None,
            final_layer=config.estimator_final_layer,
            wavenet_hidden_dim=config.estimator_wavenet_hidden_dim,
            wavenet_kernel_size=config.estimator_wavenet_kernel_size,
            wavenet_dilation_rate=config.estimator_wavenet_dilation_rate,
            wavenet_num_layers=config.estimator_wavenet_num_layers,
            wavenet_dropout=config.estimator_wavenet_dropout,
        )

        self.input_embedding = SemanticTokenEmbedding(
            codebook_size=config.semantic_codebook_size,
            codebook_dim=config.semantic_codebook_dim,
            output_dim=config.semantic_output_dim,
        )
        self.encoder_proj = nn.Linear(self.lm_latent_dim + self.semantic_embed_dim, config.lr_in_channels)
        self.prompt_cond = nn.Parameter(torch.zeros(1, 1, config.lr_out_channels))
        nn.init.normal_(self.prompt_cond, mean=0.0, std=0.02)


    def forward(self, batch: Dict[str, torch.Tensor], device: Optional[torch.device] = None) -> Dict[str, torch.Tensor]:
        """Training forward pass with prompt conditioning.

        Args:
            batch: Dict with keys:
                - semantic_token: Semantic token IDs, shape (B, T_sem)
                - semantic_token_len: Valid lengths, shape (B,)
                - lm_latent: LLM hidden states from T2S, shape (B, T_sem, D_lm)
                - speech_feat: Target mel-spectrogram, shape (B, T_mel, n_mels)
                - speech_feat_len: Valid mel lengths, shape (B,)
                - embedding: Speaker style embedding, shape (B, D_spk)
            device: Target device

        Returns:
            Dict with "loss": scalar tensor
        """
        semantic_token = batch["semantic_token"]
        semantic_token_len = batch["semantic_token_len"]
        lm_latent = batch["lm_latent"]
        feat = batch["speech_feat"]
        feat_len = batch["speech_feat_len"]
        embedding = batch["embedding"]

        if device is None:
            device = feat.device

        batch_size = feat.size(0)

        # Embed semantic tokens
        semantic_emb = self.input_embedding(semantic_token).transpose(1, 2)  # (B, T_sem, D_sem)
        token_mask = (~make_pad_mask(semantic_token_len)).float().unsqueeze(-1).to(device)
        semantic_emb = semantic_emb * token_mask

        # Combine semantic and LLM features, then upsample to mel frame rate
        frame_cond_tokens = self.encoder_proj(torch.cat([lm_latent, semantic_emb], dim=-1))
        h, h_lengths = self.length_regulator(frame_cond_tokens, feat_len)

        # Random prompt masking for training robustness (0-30% of mel)
        prompt_len = (torch.rand([batch_size], device=device) * feat_len * 0.3).floor().long()

        for i in range(batch_size):
            if prompt_len[i] > 0:
                placeholder_expanded = self.prompt_cond.expand(1, prompt_len[i], -1)
                h[i, :prompt_len[i]] = placeholder_expanded[0]

        feat_mask = (~make_pad_mask(feat_len)).to(h)

        # Compute flow matching loss
        loss, _ = self.decoder.compute_loss(
            x1=feat.transpose(1, 2).contiguous(),
            mask=feat_mask.unsqueeze(1),
            mu=h,
            spks=embedding,
            prompt_lens=prompt_len,
        )
        return {"loss": loss}

    @torch.no_grad()
    def inference(
        self,
        semantic_token: torch.Tensor,
        lm_latent: torch.Tensor,
        prompt_feat: torch.Tensor,
        embedding: torch.Tensor,
        target_feat_len: torch.Tensor,
        n_timesteps: int = 25,
        inference_cfg_rate: float = 0.7,
    ) -> torch.Tensor:
        """Generate mel-spectrogram from semantic tokens with prompt conditioning.

        Args:
            semantic_token: Semantic token IDs, shape (B, T_sem)
            lm_latent: LLM hidden states from T2S, shape (B, T_sem, D_lm)
            prompt_feat: Reference mel-spectrogram, shape (B, T_prompt, n_mels)
            embedding: Speaker style embedding, shape (B, D_spk)
            target_feat_len: Target mel length (without prompt), shape (B,)
            n_timesteps: Number of ODE solver steps
            inference_cfg_rate: Classifier-free guidance scale

        Returns:
            Generated mel-spectrogram, shape (B, n_mels, T_target)
        """
        batch_size = semantic_token.size(0)
        device = semantic_token.device

        # Embed and project semantic tokens + LLM features
        semantic_emb = self.input_embedding(semantic_token).transpose(1, 2)

        combined_features = torch.cat([lm_latent, semantic_emb], dim=-1)
        text_cond = self.encoder_proj(combined_features)

        # Upsample to target mel length
        cond_target, _ = self.length_regulator(text_cond, target_feat_len)

        # Prepend prompt condition
        T_ref = prompt_feat.size(1)
        prompt_condition = self.prompt_cond.expand(batch_size, T_ref, -1)

        cat_condition = torch.cat([prompt_condition, cond_target], dim=1)
        total_lengths = torch.full((batch_size,), T_ref, device=device) + target_feat_len

        # Generate mel via flow matching ODE
        generated_mel = self.decoder.forward(
            mu=cat_condition,
            x_lens=total_lengths,
            prompt=prompt_feat.transpose(1, 2).contiguous(),
            spks=embedding,
            n_timesteps=n_timesteps,
            inference_cfg_rate=inference_cfg_rate,
            temperature=1.0,
        )

        # Remove prompt portion
        generated_mel = generated_mel[:, :, T_ref:]
        return generated_mel
