"""Processor for MOSS-Transcribe-Diarize audio-text inference."""

from __future__ import annotations

from typing import Optional, Union

import numpy as np
import torch
from transformers.feature_extraction_utils import BatchFeature
from transformers.processing_utils import ProcessingKwargs, ProcessorMixin, Unpack


AUDIO_PAD_TOKEN = "<|audio_pad|>"
AUDIO_START_TOKEN = "<|audio_start|>"
AUDIO_END_TOKEN = "<|audio_end|>"
WHISPER_ENCODER_STRIDE = 2


class MossTranscribeDiarizeProcessorKwargs(ProcessingKwargs, total=False):
    _defaults = {
        "common_kwargs": {
            "return_tensors": "pt",
        },
        "audio_kwargs": {},
    }


def _audio_to_numpy(audio: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
    if torch.is_tensor(audio):
        audio = audio.detach().cpu().numpy()
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.squeeze(audio)
    if audio.ndim == 0:
        audio = audio.reshape(1)
    if audio.ndim != 1:
        raise ValueError(f"Expected mono audio with shape (num_samples,), got shape {audio.shape}.")
    if audio.shape[0] == 0:
        raise ValueError("Audio must contain at least one sample.")
    return audio


def _pad_or_trim_audio(audio: np.ndarray, length: int) -> np.ndarray:
    if audio.shape[0] > length:
        audio = audio[:length]
    elif audio.shape[0] < length:
        audio = np.pad(audio, (0, length - audio.shape[0]))
    return audio.astype(np.float32, copy=False)


def _compute_audio_token_length(num_samples: int, feature_extractor, audio_merge_size: int) -> int:
    stride = int(feature_extractor.hop_length) * WHISPER_ENCODER_STRIDE * int(audio_merge_size)
    return (int(num_samples) - 1) // stride + 1


def _chunk_audio(
    feature_extractor,
    audio: Union[np.ndarray, torch.Tensor],
    audio_merge_size: int,
) -> tuple[np.ndarray, list[int]]:
    audio = _audio_to_numpy(audio)
    n_samples = int(feature_extractor.n_samples)

    chunks, token_lengths = [], []
    for start in range(0, audio.shape[0], n_samples):
        chunk = audio[start : start + n_samples]
        token_lengths.append(_compute_audio_token_length(chunk.shape[0], feature_extractor, audio_merge_size))
        chunks.append(_pad_or_trim_audio(chunk, n_samples))
    return np.stack(chunks), token_lengths


def _audios_to_input_features(
    feature_extractor,
    audios: list[Union[np.ndarray, torch.Tensor]],
    *,
    audio_merge_size: int,
    feature_extractor_kwargs: Optional[dict] = None,
) -> tuple[torch.Tensor, torch.LongTensor, torch.LongTensor]:
    feature_batches, feature_lengths, chunk_mapping = [], [], []
    feature_extractor_kwargs = dict(feature_extractor_kwargs or {})
    feature_extractor_kwargs.update(
        {
            "sampling_rate": int(feature_extractor.sampling_rate),
            "padding": "max_length",
            "return_tensors": "pt",
        }
    )

    for audio_idx, audio in enumerate(audios):
        chunks, token_lengths = _chunk_audio(feature_extractor, audio, audio_merge_size)
        features = feature_extractor(
            list(chunks),
            **feature_extractor_kwargs,
        )["input_features"]
        feature_batches.append(features)
        feature_lengths.extend(token_lengths)
        chunk_mapping.extend([audio_idx] * len(token_lengths))

    if feature_batches:
        input_features = torch.cat(feature_batches, dim=0)
    else:
        input_features = torch.empty(
            (0, int(feature_extractor.feature_size), int(feature_extractor.nb_max_frames)),
        )

    length_device = input_features.device
    return (
        input_features,
        torch.tensor(feature_lengths, dtype=torch.long, device=length_device),
        torch.tensor(chunk_mapping, dtype=torch.long, device=length_device),
    )


class MossTranscribeDiarizeProcessor(ProcessorMixin):
    """Build MOSS-Transcribe-Diarize model inputs from text prompts and raw waveforms.

    The model consumes log-mel ``input_features``. This processor owns the raw
    waveform preprocessing, audio placeholder expansion, and optional numeric
    time anchors inside the audio span.
    """

    attributes = ["feature_extractor", "tokenizer"]
    feature_extractor_class = "AutoFeatureExtractor"
    tokenizer_class = "AutoTokenizer"

    model_input_names = [
        "input_ids",
        "attention_mask",
        "input_features",
        "audio_feature_lengths",
        "audio_chunk_mapping",
    ]

    def __init__(
        self,
        feature_extractor=None,
        tokenizer=None,
        audio_tokens_per_second: float = 12.5,
        audio_merge_size: int = 4,
        time_marker_every_seconds: int = 2,
        enable_time_marker: bool = True,
        chat_template: Optional[str] = None,
    ):
        if feature_extractor is None:
            raise ValueError("MossTranscribeDiarizeProcessor requires a feature_extractor.")
        if tokenizer is None:
            raise ValueError("MossTranscribeDiarizeProcessor requires a tokenizer.")
        super().__init__(feature_extractor, tokenizer, chat_template=chat_template)
        self.audio_tokens_per_second = audio_tokens_per_second
        self.audio_merge_size = int(audio_merge_size)
        self.time_marker_every_seconds = time_marker_every_seconds
        self.enable_time_marker = enable_time_marker
        self.audio_token = AUDIO_PAD_TOKEN if not hasattr(tokenizer, "audio_token") else tokenizer.audio_token
        self.audio_start_token = (
            AUDIO_START_TOKEN if not hasattr(tokenizer, "audio_start_token") else tokenizer.audio_start_token
        )
        self.audio_end_token = AUDIO_END_TOKEN if not hasattr(tokenizer, "audio_end_token") else tokenizer.audio_end_token
        resolved_audio_token_id = tokenizer.convert_tokens_to_ids(self.audio_token)
        if resolved_audio_token_id is None:
            raise ValueError(f"Tokenizer is missing required audio placeholder token {self.audio_token!r}.")
        self.audio_token_id = int(resolved_audio_token_id)
        self.digit_token_ids = self._get_digit_token_ids()

    def _get_digit_token_ids(self) -> dict[str, int]:
        digit_token_ids = {}
        for digit in "0123456789":
            ids = self.tokenizer.encode(digit, add_special_tokens=False)
            if len(ids) != 1:
                raise ValueError(f"Digit {digit!r} is not a single token: {ids}")
            digit_token_ids[digit] = int(ids[0])
        return digit_token_ids

    def _audio_span_ids(self, audio_seq_len: int) -> list[int]:
        audio_seq_len = int(audio_seq_len)
        if not self.enable_time_marker or audio_seq_len <= 0 or self.time_marker_every_seconds <= 0:
            return [self.audio_token_id] * max(audio_seq_len, 0)

        tokens_per_marker = int(self.audio_tokens_per_second * self.time_marker_every_seconds)
        if tokens_per_marker <= 0:
            return [self.audio_token_id] * audio_seq_len

        duration = audio_seq_len / float(self.audio_tokens_per_second)
        output, consumed = [], 0
        for sec in range(self.time_marker_every_seconds, int(duration) + 1, self.time_marker_every_seconds):
            pos = (sec // self.time_marker_every_seconds) * tokens_per_marker
            segment_len = pos - consumed
            if segment_len > 0:
                output.extend([self.audio_token_id] * segment_len)
                consumed += segment_len
            marker_ids = [self.digit_token_ids[digit] for digit in str(sec)]
            output.extend(marker_ids)

        remainder = audio_seq_len - consumed
        if remainder > 0:
            output.extend([self.audio_token_id] * remainder)
        return output

    def expand_audio_token(self, text: str, num_audio_tokens: int, max_length: int) -> list[int]:
        """Replace the audio placeholder with audio and time-marker token IDs."""
        audio_ids = self._audio_span_ids(num_audio_tokens)
        audio_token_count = text.count(self.audio_token)
        if audio_token_count != 1:
            raise ValueError(
                f"Expected exactly one {self.audio_token!r} token per text sample, got {audio_token_count}."
            )
        before_audio, after_audio = text.split(self.audio_token, maxsplit=1)
        before_ids = self.tokenizer.encode(before_audio, add_special_tokens=False)
        after_ids = self.tokenizer.encode(after_audio, add_special_tokens=False)

        input_ids = before_ids + audio_ids + after_ids

        if len(input_ids) > max_length:
            raise ValueError(f"Prompt/audio sequence exceeds max_length={max_length}")
        return input_ids

    def __call__(
        self,
        text: Union[str, list[str]],
        audio,
        *,
        max_length: int = 131072,
        **kwargs: Unpack[MossTranscribeDiarizeProcessorKwargs],
    ) -> BatchFeature:
        return_tensors = kwargs.pop("return_tensors", "pt")
        output_kwargs = self._merge_kwargs(
            MossTranscribeDiarizeProcessorKwargs,
            tokenizer_init_kwargs=self.tokenizer.init_kwargs,
            **kwargs,
        )
        if isinstance(text, str):
            texts = [text]
        else:
            texts = list(text)
        audios = audio if isinstance(audio, list) else [audio]
        if len(texts) != len(audios):
            raise ValueError(f"Expected one audio per text prompt, got {len(audios)} audios and {len(texts)} prompts.")

        input_features, audio_feature_lengths, audio_chunk_mapping = _audios_to_input_features(
            self.feature_extractor,
            audios,
            audio_merge_size=self.audio_merge_size,
            feature_extractor_kwargs=output_kwargs["audio_kwargs"],
        )
        audio_token_counts = torch.zeros(len(audios), dtype=torch.long, device=audio_feature_lengths.device)
        audio_token_counts.scatter_add_(0, audio_chunk_mapping, audio_feature_lengths)

        encoded = [
            self.expand_audio_token(prompt, int(num_audio_tokens.item()), max_length)
            for prompt, num_audio_tokens in zip(texts, audio_token_counts)
        ]
        max_seq_len = max(len(ids) for ids in encoded)
        pad_token_id = self.tokenizer.pad_token_id
        if pad_token_id is None:
            pad_token_id = self.tokenizer.eos_token_id or 0

        input_ids, attention_mask = [], []
        for ids in encoded:
            pad_len = max_seq_len - len(ids)
            input_ids.append(ids + [pad_token_id] * pad_len)
            attention_mask.append([1] * len(ids) + [0] * pad_len)

        target_device = input_features.device
        data = {
            "input_ids": torch.tensor(input_ids, dtype=torch.long, device=target_device),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long, device=target_device),
            "input_features": input_features,
            "audio_feature_lengths": audio_feature_lengths,
            "audio_chunk_mapping": audio_chunk_mapping,
        }
        return BatchFeature(data=data, tensor_type=return_tensors)


__all__ = ["MossTranscribeDiarizeProcessor"]
