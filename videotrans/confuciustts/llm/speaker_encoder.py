# Copyright 2026 The Qwen team, Alibaba Group and the HuggingFace Inc. team. All rights reserved.
# Copyright 2026 NetEase Youdao. All rights reserved.
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
#
# Modified from https://github.com/QwenLM/Qwen3-TTS


import torch
from torch import nn
from torch.nn import functional as F
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Qwen3TTSSpeakerEncoderConfig:
    r"""
    This is the configuration class to store the configuration of a [`Qwen3TTSSpeakerEncoder`].
    It is used to instantiate a Qwen3TTS speaker encoder model according to the specified arguments, defining the model
    architecture. The architecture is based on the ECAPA-TDNN model.

    Args:
        mel_dim (`int`, *optional*, defaults to 128):
            The dimension of the input mel-spectrogram.
        enc_dim (`int`, *optional*, defaults to 1024):
            The dimension of the final speaker embedding.
        enc_channels (`list[int]`, *optional*, defaults to `[512, 512, 512, 512, 1536]`):
            A list of output channels for each TDNN/SERes2Net layer in the encoder. The first channel size is for the initial TDNN layer,
            the intermediate ones for the `SqueezeExcitationRes2NetBlock` layers, and the last one for the multi-layer feature aggregation.
        enc_kernel_sizes (`list[int]`, *optional*, defaults to `[5, 3, 3, 3, 1]`):
            A list of kernel sizes for each layer in the encoder, corresponding to `enc_channels`.
        enc_dilations (`list[int]`, *optional*, defaults to `[1, 2, 3, 4, 1]`):
            A list of dilations for each layer in the encoder, corresponding to `enc_channels`.
        enc_attention_channels (`int`, *optional*, defaults to 128):
            The number of attention channels in the `AttentiveStatisticsPooling` layer.
        enc_res2net_scale (`int`, *optional*, defaults to 8):
            The scale of the `Res2NetBlock` in the encoder.
        enc_se_channels (`int`, *optional*, defaults to 128):
            The number of channels in the squeeze part of the `SqueezeExcitationBlock`.
        sample_rate (`int`, *optional*, defaults to 24000):
            The sample rate of the input audio.
    """
    mel_dim: int = 128
    enc_dim: int = 1024
    enc_channels: List[int] = None
    enc_kernel_sizes: List[int] = None
    enc_dilations: List[int] = None
    enc_attention_channels: int = 128
    enc_res2net_scale: int = 8
    enc_se_channels: int = 128
    sample_rate: int = 24000
    
    def __post_init__(self):
        if self.enc_channels is None:
            self.enc_channels = [512, 512, 512, 512, 1536]
        if self.enc_kernel_sizes is None:
            self.enc_kernel_sizes = [5, 3, 3, 3, 1]
        if self.enc_dilations is None:
            self.enc_dilations = [1, 2, 3, 4, 1]


class TimeDelayNetBlock(nn.Module):
    """Time Delay Neural Network (TDNN) block with 1D convolution."""
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int,
    ):
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding="same",
            padding_mode="reflect",
        )
        self.activation = nn.ReLU()

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.activation(self.conv(hidden_states))


class Res2NetBlock(nn.Module):
    """Res2Net block for multi-scale feature extraction."""
    
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        scale: int = 8, 
        kernel_size: int = 3, 
        dilation: int = 1
    ):
        super().__init__()
        
        if in_channels % scale != 0 or out_channels % scale != 0:
            raise ValueError(f"in_channels ({in_channels}) and out_channels ({out_channels}) must be divisible by scale ({scale})")

        in_channel = in_channels // scale
        hidden_channel = out_channels // scale

        self.blocks = nn.ModuleList(
            [
                TimeDelayNetBlock(
                    in_channel,
                    hidden_channel,
                    kernel_size=kernel_size,
                    dilation=dilation,
                )
                for _ in range(scale - 1)
            ]
        )
        self.scale = scale

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        outputs = []
        chunks = torch.chunk(hidden_states, self.scale, dim=1)
        
        for i, hidden_part in enumerate(chunks):
            if i == 0:
                output_part = hidden_part
            elif i == 1:
                output_part = self.blocks[i - 1](hidden_part)
            else:
                output_part = self.blocks[i - 1](hidden_part + output_part)
            outputs.append(output_part)
            
        return torch.cat(outputs, dim=1)


class SqueezeExcitationBlock(nn.Module):
    """Squeeze-and-Excitation block for channel attention."""
    
    def __init__(self, in_channels: int, se_channels: int, out_channels: int):
        super().__init__()

        self.conv1 = nn.Conv1d(
            in_channels=in_channels,
            out_channels=se_channels,
            kernel_size=1,
            padding="same",
            padding_mode="reflect",
        )
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv1d(
            in_channels=se_channels,
            out_channels=out_channels,
            kernel_size=1,
            padding="same",
            padding_mode="reflect",
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        hidden_states_mean = hidden_states.mean(dim=2, keepdim=True)
        hidden_states_mean = self.relu(self.conv1(hidden_states_mean))
        hidden_states_mean = self.sigmoid(self.conv2(hidden_states_mean))
        return hidden_states * hidden_states_mean


class SqueezeExcitationRes2NetBlock(nn.Module):
    """Building block in ECAPA-TDNN: TDNN-Res2Net-TDNN-SE."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        res2net_scale: int = 8,
        se_channels: int = 128,
        kernel_size: int = 1,
        dilation: int = 1,
    ):
        super().__init__()
        self.out_channels = out_channels
        
        self.tdnn1 = TimeDelayNetBlock(
            in_channels,
            out_channels,
            kernel_size=1,
            dilation=1,
        )
        self.res2net_block = Res2NetBlock(
            out_channels, out_channels, res2net_scale, kernel_size, dilation
        )
        self.tdnn2 = TimeDelayNetBlock(
            out_channels,
            out_channels,
            kernel_size=1,
            dilation=1,
        )
        self.se_block = SqueezeExcitationBlock(out_channels, se_channels, out_channels)
        
        self.shortcut = None
        if in_channels != out_channels:
            self.shortcut = nn.Conv1d(in_channels, out_channels, kernel_size=1)

    def forward(self, hidden_state: torch.Tensor) -> torch.Tensor:
        residual = hidden_state
        if self.shortcut is not None:
            residual = self.shortcut(residual)

        hidden_state = self.tdnn1(hidden_state)
        hidden_state = self.res2net_block(hidden_state)
        hidden_state = self.tdnn2(hidden_state)
        hidden_state = self.se_block(hidden_state)

        return hidden_state + residual


class AttentiveStatisticsPooling(nn.Module):
    """Attentive statistics pooling layer.
    
    Returns the concatenated mean and std of the input tensor weighted by attention.
    """

    def __init__(self, channels: int, attention_channels: int = 128):
        super().__init__()

        self.eps = 1e-12
        self.tdnn = TimeDelayNetBlock(channels * 3, attention_channels, 1, 1)
        self.tanh = nn.Tanh()
        self.conv = nn.Conv1d(
            in_channels=attention_channels,
            out_channels=channels,
            kernel_size=1,
            padding="same",
            padding_mode="reflect",
        )

    def _compute_statistics(
        self, 
        x: torch.Tensor, 
        m: torch.Tensor, 
        dim: int = 2
    ) -> tuple:
        """Compute weighted mean and std."""
        mean = (m * x).sum(dim)
        std = torch.sqrt((m * (x - mean.unsqueeze(dim)).pow(2)).sum(dim).clamp(min=self.eps))
        return mean, std

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch, channels, time)
        Returns:
            pooled_stats: (batch, channels * 2, 1)
        """
        batch_size, channels, seq_length = hidden_states.shape
        
        mask = torch.ones(batch_size, 1, seq_length, device=hidden_states.device, dtype=hidden_states.dtype)
        total = mask.sum(dim=2, keepdim=True)

        mean, std = self._compute_statistics(hidden_states, mask / total)
        mean = mean.unsqueeze(2).expand(-1, -1, seq_length)
        std = std.unsqueeze(2).expand(-1, -1, seq_length)
        
        attention = torch.cat([hidden_states, mean, std], dim=1)
        attention = self.conv(self.tanh(self.tdnn(attention)))
        attention = F.softmax(attention, dim=2)
        
        mean, std = self._compute_statistics(hidden_states, attention)
        pooled_stats = torch.cat((mean, std), dim=1)
        pooled_stats = pooled_stats.unsqueeze(2)

        return pooled_stats


class Qwen3TTSSpeakerEncoder(nn.Module):
    """ECAPA-TDNN based speaker encoder for Qwen3TTS.
    
    Reference: "ECAPA-TDNN: Emphasized Channel Attention, Propagation and Aggregation in
    TDNN Based Speaker Verification" (https://arxiv.org/abs/2005.07143)
    """

    def __init__(self, config: Qwen3TTSSpeakerEncoderConfig):
        super().__init__()
        self.config = config
        
        # Verify configuration
        if len(config.enc_channels) != len(config.enc_kernel_sizes) or \
           len(config.enc_channels) != len(config.enc_dilations):
            raise ValueError(
                f"enc_channels ({len(config.enc_channels)}), "
                f"enc_kernel_sizes ({len(config.enc_kernel_sizes)}) and "
                f"enc_dilations ({len(config.enc_dilations)}) should have same length"
            )
        
        self.channels = config.enc_channels
        self.blocks = nn.ModuleList()

        # TDNN layer
        self.blocks.append(
            TimeDelayNetBlock(
                config.mel_dim,
                config.enc_channels[0],
                config.enc_kernel_sizes[0],
                config.enc_dilations[0],
            )
        )

        # SE-Res2Net
        for i in range(1, len(config.enc_channels) - 1):
            self.blocks.append(
                SqueezeExcitationRes2NetBlock(
                    config.enc_channels[i - 1],
                    config.enc_channels[i],
                    res2net_scale=config.enc_res2net_scale,
                    se_channels=config.enc_se_channels,
                    kernel_size=config.enc_kernel_sizes[i],
                    dilation=config.enc_dilations[i],
                )
            )

        mfa_in_channels = sum(config.enc_channels[1:-1])
        self.mfa = TimeDelayNetBlock(
            mfa_in_channels,
            config.enc_channels[-1],
            config.enc_kernel_sizes[-1],
            config.enc_dilations[-1],
        )

        self.asp = AttentiveStatisticsPooling(
            config.enc_channels[-1],
            attention_channels=config.enc_attention_channels,
        )

        self.fc = nn.Conv1d(
            in_channels=config.enc_channels[-1] * 2,
            out_channels=config.enc_dim,
            kernel_size=1,
            padding="same",
            padding_mode="reflect",
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch, time, mel_dim) - 输入 mel 特征
            
        Returns:
            embeddings: (batch, enc_dim) - speaker embedding
        """
        hidden_states = hidden_states.transpose(1, 2)

        hidden_states_list = []
        for layer in self.blocks:
            hidden_states = layer(hidden_states)
            hidden_states_list.append(hidden_states)

        # multi-layer feature aggregation (skipping the first layer)
        hidden_states = torch.cat(hidden_states_list[1:], dim=1)
        hidden_states = self.mfa(hidden_states)
        # Attention Statistical Pooling
        hidden_states = self.asp(hidden_states)
        hidden_states = self.fc(hidden_states)
        # (batch, dim, 1) -> (batch, dim)
        hidden_states = hidden_states.squeeze(-1)
        return hidden_states
    
    @torch.no_grad()
    def extract_embedding(self, mel_features: torch.Tensor) -> torch.Tensor:
        """extract speaker embeddings from mel features.
        
        Args:
            mel_features: (batch, time, mel_dim) or (time, mel_dim)
            
        Returns:
            embeddings: (batch, enc_dim) or (enc_dim,)
        """
        self.eval()
        
        squeeze = False
        if mel_features.dim() == 2:
            mel_features = mel_features.unsqueeze(0)
            squeeze = True
            
        embeddings = self.forward(mel_features)
        
        embeddings = F.normalize(embeddings, p=2, dim=-1)
        
        if squeeze:
            embeddings = embeddings.squeeze(0)
            
        return embeddings
    
    def get_embedding_dim(self) -> int:
        """return dimension of embedding."""
        return self.config.enc_dim
