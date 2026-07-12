from typing import Optional

import torch
import torchaudio
from librosa.filters import mel as librosa_mel_fn


_MEL_TRANSFORMS: dict = {}
_FBANK_TRANSFORMS: dict = {}
_MEL_BASIS_CACHE: dict = {}
_HANN_WINDOW_CACHE: dict = {}


def _get_mel_transform(
    sample_rate: int,
    n_fft: int,
    win_length: int,
    hop_length: int,
    n_mels: int,
    f_min: float,
    f_max: Optional[float],
    device: torch.device,
) -> torchaudio.transforms.MelSpectrogram:
    key = (sample_rate, n_fft, win_length, hop_length, n_mels, f_min, f_max, str(device))
    tx = _MEL_TRANSFORMS.get(key)
    if tx is None:
        tx = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            win_length=win_length,
            hop_length=hop_length,
            n_mels=n_mels,
            f_min=f_min,
            f_max=f_max,
            power=1.0,
            center=True,
            pad_mode="reflect",
            mel_scale="slaney",
            norm="slaney",
        ).to(device)
        _MEL_TRANSFORMS[key] = tx
    return tx


def extract_mel(
    waveform: torch.Tensor,
    sample_rate: int = 22050,
    n_fft: int = 1024,
    win_length: int = 1024,
    hop_length: int = 256,
    n_mels: int = 80,
    f_min: float = 0.0,
    f_max: Optional[float] = None,
    log_eps: float = 1e-5,
) -> torch.Tensor:
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.size(0) > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    tx = _get_mel_transform(
        sample_rate, n_fft, win_length, hop_length, n_mels, f_min, f_max, waveform.device
    )
    mel = tx(waveform)
    mel = torch.log(mel.clamp_min(log_eps))
    return mel.squeeze(0).transpose(0, 1).contiguous()


def mel_spectrogram(
    audio: torch.Tensor,
    sample_rate: int,
    n_fft: int,
    hop_length: int,
    win_length: int,
    n_mels: int,
    fmin: float,
    fmax: Optional[float],
) -> torch.Tensor:
    device = audio.device
    key = (n_fft, n_mels, sample_rate, hop_length, win_length, fmin, fmax, str(device))
    if key not in _MEL_BASIS_CACHE:
        mel = librosa_mel_fn(sr=sample_rate, n_fft=n_fft, n_mels=n_mels, fmin=fmin, fmax=fmax)
        _MEL_BASIS_CACHE[key] = torch.from_numpy(mel).float().to(device)
        _HANN_WINDOW_CACHE[key] = torch.hann_window(win_length).to(device)
    mel_basis = _MEL_BASIS_CACHE[key]
    hann_window = _HANN_WINDOW_CACHE[key]

    pad = (n_fft - hop_length) // 2
    y = torch.nn.functional.pad(audio.unsqueeze(1), (pad, pad), mode="reflect").squeeze(1)
    spec = torch.view_as_real(torch.stft(
        y, n_fft, hop_length=hop_length, win_length=win_length,
        window=hann_window, center=False, pad_mode="reflect",
        normalized=False, onesided=True, return_complex=True,
    ))
    spec = torch.sqrt(spec.pow(2).sum(-1) + 1e-9)
    spec = torch.matmul(mel_basis, spec)
    return torch.log(torch.clamp(spec, min=1e-5))


def extract_fbank(
    waveform: torch.Tensor,
    sample_rate: int = 16000,
    n_mels: int = 80,
    frame_length: float = 25.0,
    frame_shift: float = 10.0,
) -> torch.Tensor:
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.size(0) > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    feat = torchaudio.compliance.kaldi.fbank(
        waveform,
        num_mel_bins=n_mels,
        sample_frequency=sample_rate,
        frame_length=frame_length,
        frame_shift=frame_shift,
        dither=0.0,
    )
    feat = feat - feat.mean(dim=0, keepdim=True)
    return feat
