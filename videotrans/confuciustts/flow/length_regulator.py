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

from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from videotrans.confuciustts.utils.mask import make_pad_mask


class InterpolateRegulator(nn.Module):

    def __init__(
        self,
        channels: int,
        sampling_ratios: Tuple[int, ...],
        out_channels: Optional[int] = None,
        groups: int = 1,
        in_channels: Optional[int] = None,
    ):
        super().__init__()
        self.sampling_ratios = tuple(sampling_ratios)
        self.in_channels = in_channels or channels
        out_channels = out_channels or channels

        self.content_in_proj = nn.Linear(self.in_channels, channels)

        layers = []
        for _ in self.sampling_ratios:
            layers.append(nn.Conv1d(channels, channels, kernel_size=3, padding=1))
            layers.append(nn.GroupNorm(groups, channels))
            layers.append(nn.Mish())
        layers.append(nn.Conv1d(channels, out_channels, kernel_size=1))
        self.model = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor, ylens: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.content_in_proj(x)

        target_len = int(ylens.max().item())
        mask = (~make_pad_mask(ylens, max_len=target_len)).to(x.dtype).unsqueeze(-1)

        x = F.interpolate(x.transpose(1, 2).contiguous(), size=target_len, mode="nearest")

        out = self.model(x).transpose(1, 2).contiguous()
        return out * mask, ylens
