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
import torch.nn as nn


class TextEmbeddingProjector(nn.Module):
    """
    MLP for resizing text embedding dimension.
    Reference: Qwen3TTSTalkerResizeMLP from https://github.com/QwenLM/Qwen3-TTS.
    
    Structure: Embedding -> Linear(input_size, intermediate_size) -> Act -> Linear(intermediate_size, output_size)
    """
    def __init__(
        self, 
        vocab_size: int, 
        embed_dim: int, 
        output_size: int, 
        hidden_act: str = "silu", 
        bias: bool = True,
    ):
        super().__init__()
        
        # Initialize embedding layer and load pretrained weights
        self.embed = nn.Embedding(vocab_size, embed_dim)
        
        # Freeze embedding weights
        self.embed.weight.requires_grad = False
        self.embed.eval()
        
        # Text projection MLP (following Qwen3TTSTalkerResizeMLP structure)
        self.text_projection_fc1 = nn.Linear(embed_dim, embed_dim, bias=bias)
        self.text_projection_fc2 = nn.Linear(embed_dim, output_size, bias=bias)
        
        # Activation function
        if hidden_act == "silu":
            self.act_fn = nn.SiLU()
        elif hidden_act == "gelu":
            self.act_fn = nn.GELU()
        elif hidden_act == "relu":
            self.act_fn = nn.ReLU()
        else:
            self.act_fn = nn.SiLU()  # Default to SiLU
    
        # Initialize projection layers
        nn.init.normal_(self.text_projection_fc1.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.text_projection_fc2.weight, mean=0.0, std=0.02)
        if bias:
            nn.init.zeros_(self.text_projection_fc1.bias)
            nn.init.zeros_(self.text_projection_fc2.bias)

    def forward(self, text_ids: torch.Tensor) -> torch.Tensor:
        """Resize text embeddings through MLP projection."""
        with torch.no_grad():
            text_embeds = self.embed(text_ids)
        # MLP projection: fc1 -> act -> fc2
        return self.text_projection_fc2(self.act_fn(self.text_projection_fc1(text_embeds)))
    
    def load_pretrained_embeddings(self, pretrained_weights: torch.Tensor):
        """Load pretrained embedding weights."""
        self.embed.weight.data.copy_(pretrained_weights)
        self.embed.weight.requires_grad = False
