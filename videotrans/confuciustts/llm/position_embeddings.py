import torch
import torch.nn as nn


class DummyPositionEmbedding(nn.Module):
    """Placeholder position embedding that returns zeros.
    Args:
        embedding_dim: Dimension of embeddings
    """
    def __init__(self, embedding_dim: int):
        super().__init__()
        self.embedding_dim = embedding_dim

    def forward(self, position_ids: torch.Tensor) -> torch.Tensor:
        """Return zero embeddings.

        Args:
            position_ids: Position indices, shape (B, T)

        Returns:
            Zero tensor, shape (B, T, embedding_dim)
        """
        batch_size, seq_len = position_ids.shape
        return torch.zeros(
            batch_size, seq_len, self.embedding_dim,
            dtype=torch.float32,
            device=position_ids.device
        )


class LearnedPositionalEmbedding(nn.Module):
    """Learned positional embedding with additive combination.

    Args:
        max_seq_len: Maximum sequence length
        embedding_dim: Dimension of embeddings
        init_std: Standard deviation for weight initialization
    """
    def __init__(self, max_seq_len: int, embedding_dim: int, init_std: float = 0.02):
        super().__init__()
        self.embedding = nn.Embedding(max_seq_len, embedding_dim)
        self.embedding.weight.data.normal_(mean=0.0, std=init_std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional embeddings to input.

        Args:
            x: Input tensor, shape (B, T, D)

        Returns:
            Input with positional embeddings added, shape (B, T, D)
        """
        seq_len = x.shape[1]
        positions = torch.arange(seq_len, device=x.device)
        return x + self.embedding(positions).unsqueeze(0).expand(x.shape[0], -1, -1)

    def get_fixed_embedding(self, position: int, device: torch.device) -> torch.Tensor:
        """Get embedding for a specific position (used in KV-cached generation).

        Args:
            position: Position index
            device: Target device

        Returns:
            Position embedding, shape (1, 1, D)
        """
        pos_tensor = torch.tensor([position], device=device)
        return self.embedding(pos_tensor).unsqueeze(0)
