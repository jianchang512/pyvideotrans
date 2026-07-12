
import torch
import torch.nn as nn
import torch.nn.functional as F


class SemanticTokenEmbedding(nn.Module):
    def __init__(
        self,
        codebook_size: int = 8192,
        codebook_dim: int = 8,
        output_dim: int = 1024
    ):
        super().__init__()
        self.embedding = nn.Embedding(codebook_size, codebook_dim)
        self.out_project = nn.Conv1d(codebook_dim, output_dim, kernel_size=1)

    def forward(self, vq_codes):
        emb = self.embedding(vq_codes)
        out = self.out_project(emb.transpose(1, 2))
        return out

