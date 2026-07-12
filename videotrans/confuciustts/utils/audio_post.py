from typing import List

import torch


def fade_and_pad(
    audio: torch.Tensor,
    sample_rate: int,
    fade_duration: float = 0.1,
    pad_duration: float = 0.1,
) -> torch.Tensor:
    if audio.shape[-1] == 0:
        return audio
    fade_n = int(fade_duration * sample_rate)
    pad_n = int(pad_duration * sample_rate)
    out = audio.clone()
    k = min(fade_n, out.shape[-1] // 2)
    if k > 0:
        ramp = torch.linspace(0, 1, k, device=out.device, dtype=out.dtype)
        out[..., :k] *= ramp
        out[..., -k:] *= ramp.flip(0)
    if pad_n > 0:
        silence = torch.zeros(out.shape[0], pad_n, device=out.device, dtype=out.dtype)
        out = torch.cat([silence, out, silence], dim=-1)
    return out


def cross_fade_concat(
    chunks: List[torch.Tensor],
    sample_rate: int,
    silence_duration: float = 0.3,
) -> torch.Tensor:
    if len(chunks) == 1:
        return chunks[0]
    total_n = int(silence_duration * sample_rate)
    fade_n = total_n // 3
    silence_n = fade_n
    merged = chunks[0].clone()
    C = chunks[0].shape[0]
    for chunk in chunks[1:]:
        fout_n = min(fade_n, merged.shape[-1])
        if fout_n > 0:
            w_out = torch.linspace(1, 0, fout_n, device=merged.device, dtype=merged.dtype)
            merged[..., -fout_n:] *= w_out
        silence = torch.zeros(C, silence_n, device=merged.device, dtype=merged.dtype)
        nxt = chunk.clone()
        fin_n = min(fade_n, nxt.shape[-1])
        if fin_n > 0:
            w_in = torch.linspace(0, 1, fin_n, device=nxt.device, dtype=nxt.dtype)
            nxt[..., :fin_n] *= w_in
        merged = torch.cat([merged, silence, nxt], dim=-1)
    return merged
