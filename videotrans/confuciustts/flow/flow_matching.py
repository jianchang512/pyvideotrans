# Copyright (c) 2024 Alibaba Inc (authors: Xiang Lyu, Zhihao Du)
#               2025 Alibaba Inc (authors: Xiang Lyu, Bofan Zhou)
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

import torch
import torch.nn as nn
import torch.nn.functional as F

from videotrans.confuciustts.flow.DiT.dit import DiT


class ConditionalCFM(nn.Module):
    """Conditional Flow Matching decoder with classifier-free guidance.

    Trains a velocity field estimator to transform noise to mel-spectrogram
    conditioned on semantic features and speaker style.

    Args:
        sigma_min: Minimum noise level for numerical stability
        training_cfg_rate: Probability of dropping conditions during training
        inference_cfg_rate: CFG scale at inference (higher = stronger conditioning)
        t_scheduler: Time scheduler ("linear" or "cosine")
        hidden_dim: DiT hidden dimension
        num_heads: Number of attention heads in DiT
        depth: Number of DiT layers
        mel_dim: Mel-spectrogram dimension
        cond_dim: Conditioning vector dimension
        style_dim: Speaker style embedding dimension
        long_skip_connection: Enable U-Net-style skip connections
        final_layer: Final layer type ("wavenet" or other)
        wavenet_*: WaveNet final layer parameters
    """
    def __init__(
        self,
        sigma_min: float = 1e-6,
        training_cfg_rate: float = 0.2,
        inference_cfg_rate: float = 0.7,
        t_scheduler: str = "cosine",
        hidden_dim: int = 512,
        num_heads: int = 8,
        depth: int = 13,
        mel_dim: int = 80,
        cond_dim: int = 512,
        style_dim: int = 192,
        long_skip_connection: bool = True,
        ff_intermediate_size: int | None = None,
        final_layer: str = "wavenet",
        wavenet_hidden_dim: int = 512,
        wavenet_kernel_size: int = 5,
        wavenet_dilation_rate: int = 1,
        wavenet_num_layers: int = 8,
        wavenet_dropout: float = 0.0,
    ):
        super().__init__()

        self.sigma_min = sigma_min
        self.t_scheduler = t_scheduler
        self.training_cfg_rate = training_cfg_rate
        self.inference_cfg_rate = inference_cfg_rate
        self.mel_dim = mel_dim

        self.estimator = DiT(
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            depth=depth,
            mel_dim=mel_dim,
            mu_dim=cond_dim,
            spk_dim=style_dim,
            long_skip_connection=long_skip_connection,
            ff_intermediate_size=ff_intermediate_size,
            final_layer=final_layer,
            wavenet_hidden_dim=wavenet_hidden_dim,
            wavenet_kernel_size=wavenet_kernel_size,
            wavenet_dilation_rate=wavenet_dilation_rate,
            wavenet_num_layers=wavenet_num_layers,
            wavenet_dropout=wavenet_dropout,
        )

    def compute_loss(self, x1: torch.Tensor, mask: torch.Tensor, mu: torch.Tensor, spks: torch.Tensor, prompt_lens: torch.Tensor):
        b, _, t = x1.shape
        device = x1.device

        t_rand = torch.rand([b, 1, 1], device=device, dtype=x1.dtype)
        if self.t_scheduler == "cosine":
            t_rand = 1.0 - torch.cos(t_rand * 0.5 * torch.pi)

        z = torch.randn_like(x1)

        y = (1 - (1 - self.sigma_min) * t_rand) * z + t_rand * x1
        u = x1 - (1 - self.sigma_min) * z

        x_lens = mask.squeeze(1).sum(dim=1).long()

        prompt = torch.zeros_like(x1)
        loss_mask = torch.zeros_like(x1)
        for i in range(b):
            pl = prompt_lens[i]
            xl = x_lens[i]
            if pl > 0:
                prompt[i, :, :pl] = x1[i, :, :pl]
                y[i, :, :pl] = 0

            loss_mask[i, :, pl:xl] = 1.0

        if self.training_cfg_rate > 0:
            cfg_mask = torch.rand(b, device=x1.device) > self.training_cfg_rate
            mu = mu * cfg_mask.view(-1, 1, 1)
            spks = spks * cfg_mask.view(-1, 1)
            prompt = prompt * cfg_mask.view(-1, 1, 1)

        pred = self.estimator(y, mask.squeeze(1), mu, t_rand.squeeze(), spks, prompt)

        loss = F.l1_loss(pred * loss_mask, u * loss_mask, reduction="sum") / loss_mask.sum()
        return loss, y

    @torch.no_grad()
    def forward(self, mu: torch.Tensor, x_lens: torch.Tensor, prompt: torch.Tensor,spks: torch.Tensor, n_timesteps: int = 25, inference_cfg_rate: float = 0.7, temperature: float = 1.0):
        b, t = mu.size(0), mu.size(1)
        z = torch.randn(b, self.mel_dim, t, device=mu.device, dtype=mu.dtype) * temperature

        t_span = torch.linspace(0, 1, n_timesteps + 1, device=mu.device, dtype=mu.dtype)
        if self.t_scheduler == "cosine":
            t_span = 1 - torch.cos(t_span * 0.5 * torch.pi)

        cfg_rate = inference_cfg_rate if inference_cfg_rate is not None else self.inference_cfg_rate

        return self.solve_euler(z, t_span=t_span, x_lens=x_lens, prompt=prompt, mu=mu, spks=spks, cfg_rate=cfg_rate)

    def solve_euler(self, x, t_span, x_lens, prompt, mu, spks, cfg_rate):
        t, _, dt = t_span[0], t_span[1], t_span[1] - t_span[0]

        sol = []

        prompt_len = prompt.size(-1)
        prompt_x = torch.zeros_like(x)
        prompt_x[..., :prompt_len] = prompt[..., :prompt_len]
        x[..., :prompt_len] = 0

        # Create mask from x_lens
        batch_size = x.size(0)
        max_len = x.size(2)
        mask = torch.arange(max_len, device=x.device).unsqueeze(0) < x_lens.unsqueeze(1)

        # Do not use concat, it may cause memory format changed and trt infer with wrong results!
        # NOTE when flow run in amp mode, x.dtype is float32, which cause nan in trt fp16 inference, so set dtype=spks.dtype
        x_in = torch.zeros([2 * batch_size, self.mel_dim, x.size(2)], device=x.device, dtype=spks.dtype)
        prompt_x_in = torch.zeros([2 * batch_size, self.mel_dim, x.size(2)], device=x.device, dtype=spks.dtype)
        mu_in = torch.zeros([2 * batch_size, mu.size(1), mu.size(2)], device=x.device, dtype=spks.dtype)
        t_in = torch.zeros([2 * batch_size], device=x.device, dtype=spks.dtype)
        spks_in = torch.zeros([2 * batch_size, spks.size(1)], device=x.device, dtype=spks.dtype)
        mask_in = torch.zeros([2 * batch_size, max_len], device=x.device, dtype=torch.bool)

        for step in range(1, len(t_span)):
            if cfg_rate > 0:
                x_in[:batch_size] = x
                x_in[batch_size:] = x
                prompt_x_in[:batch_size] = prompt_x
                prompt_x_in[batch_size:] = 0
                mu_in[:batch_size] = mu
                mu_in[batch_size:] = 0
                t_in[:] = t
                spks_in[:batch_size] = spks
                spks_in[batch_size:] = 0
                mask_in[:batch_size] = mask
                mask_in[batch_size:] = mask

                dphi_dt = self.estimator(x_in, mask_in, mu_in, t_in, spks_in, prompt_x_in)
                dphi_dt, cfg_dphi_dt = torch.split(dphi_dt, [batch_size, batch_size], dim=0)
                dphi_dt = ((1.0 + cfg_rate) * dphi_dt - cfg_rate * cfg_dphi_dt)
            else:
                dphi_dt = self.estimator(x, mask, mu, t, spks, prompt_x)

            x = x + dt * dphi_dt
            t = t + dt
            sol.append(x)
            if step < len(t_span) - 1:
                dt = t_span[step + 1] - t
            x[:, :, :prompt_len] = 0

        return sol[-1].float()


