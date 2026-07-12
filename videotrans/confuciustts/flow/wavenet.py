import torch
import torch.nn as nn


def fused_add_tanh_sigmoid_multiply(input_a: torch.Tensor, input_b: torch.Tensor, n_channels: int) -> torch.Tensor:
    """Fused gated activation: tanh(x) * sigmoid(x).

    Args:
        input_a: First input tensor
        input_b: Second input tensor (added to input_a)
        n_channels: Number of channels (split point for tanh/sigmoid)

    Returns:
        Gated activation output
    """
    in_act = input_a + input_b
    t_act = torch.tanh(in_act[:, :n_channels, :])
    s_act = torch.sigmoid(in_act[:, n_channels:, :])
    return t_act * s_act


class WeightNormConv1d(nn.Module):
    """1D convolution with weight normalization.

    Args:
        in_channels: Number of input channels
        out_channels: Number of output channels
        kernel_size: Convolution kernel size
        dilation: Dilation rate
        padding: Padding size
    """
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int, dilation: int = 1, padding: int = 0):
        super().__init__()
        self.conv = nn.utils.weight_norm(
            nn.Conv1d(in_channels, out_channels, kernel_size, dilation=dilation, padding=padding)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply weight-normalized convolution.

        Args:
            x: Input tensor, shape (B, C, T)

        Returns:
            Output tensor, shape (B, out_channels, T)
        """
        return self.conv(x)


class WN(nn.Module):
    """WaveNet-style gated residual network with dilated convolutions.

    Stacks dilated convolution layers with gated activations and residual connections.
    Used as the final layer in DiT for mel-spectrogram prediction.

    Args:
        hidden_channels: Number of hidden channels
        kernel_size: Convolution kernel size
        dilation_rate: Base dilation rate (exponentially increases per layer)
        n_layers: Number of WaveNet layers
        gin_channels: Global conditioning dimension (timestep embedding)
        p_dropout: Dropout probability
    """
    def __init__(self, hidden_channels: int, kernel_size: int, dilation_rate: int, n_layers: int, gin_channels: int, p_dropout: float = 0.0):
        super().__init__()
        self.hidden_channels = hidden_channels
        self.n_layers = n_layers
        self.gin_channels = gin_channels
        self.drop = nn.Dropout(p_dropout)
        self.in_layers = nn.ModuleList()
        self.res_skip_layers = nn.ModuleList()
        self.cond_layer = WeightNormConv1d(gin_channels, 2 * hidden_channels * n_layers, 1)
        for i in range(n_layers):
            dilation = dilation_rate ** i
            padding = int((kernel_size * dilation - dilation) / 2)
            self.in_layers.append(WeightNormConv1d(hidden_channels, 2 * hidden_channels, kernel_size, dilation=dilation, padding=padding))
            res_skip_channels = 2 * hidden_channels if i < n_layers - 1 else hidden_channels
            self.res_skip_layers.append(WeightNormConv1d(hidden_channels, res_skip_channels, 1))

    def forward(self, x: torch.Tensor, x_mask: torch.Tensor, g: torch.Tensor) -> torch.Tensor:
        """WaveNet forward pass with gated convolutions and residual connections.

        Args:
            x: Input tensor, shape (B, hidden_channels, T)
            x_mask: Padding mask, shape (B, 1, T)
            g: Global conditioning (timestep embedding), shape (B, gin_channels, 1)

        Returns:
            Output tensor, shape (B, hidden_channels, T)
        """
        output = torch.zeros_like(x)
        g = self.cond_layer(g)  # Project conditioning to all layers
        for i in range(self.n_layers):
            x_in = self.in_layers[i](x)
            cond_offset = i * 2 * self.hidden_channels
            g_l = g[:, cond_offset:cond_offset + 2 * self.hidden_channels, :]
            # Gated activation: tanh(x) * sigmoid(x)
            acts = fused_add_tanh_sigmoid_multiply(x_in, g_l, self.hidden_channels)
            acts = self.drop(acts)
            res_skip_acts = self.res_skip_layers[i](acts)
            if i < self.n_layers - 1:
                # Residual connection + skip connection
                res_acts = res_skip_acts[:, :self.hidden_channels, :]
                x = (x + res_acts) * x_mask
                output = output + res_skip_acts[:, self.hidden_channels:, :]
            else:
                # Final layer: skip connection only
                output = output + res_skip_acts
        return output * x_mask
