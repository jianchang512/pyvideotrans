from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from transformers.audio_utils import load_audio
from transformers.generation.streamers import BaseStreamer


DEFAULT_PROMPT = (
    "请将音频转写为文本，每一段需以起始时间戳和说话人编号"
    "（[S01]、[S02]、[S03]…）开头，正文为对应的语音内容，"
    "并在段末标注结束时间戳，以清晰标明该段语音范围。"
)
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".flv", ".wmv"}
TokenCallback = Callable[[int], None]


class ProgressStreamer(BaseStreamer):
    """Count generated tokens from ``generate(streamer=...)`` without decoding text."""

    def __init__(self, callback: TokenCallback):
        self.callback = callback
        self.generated_tokens = 0
        self._seen_prompt = False

    def put(self, value):
        token_count = _token_count(value)
        if not self._seen_prompt:
            self._seen_prompt = True
            return
        self.generated_tokens += token_count
        self.callback(self.generated_tokens)

    def end(self):
        return None


def _token_count(value) -> int:
    if hasattr(value, "numel"):
        return int(value.numel())
    if isinstance(value, (list, tuple)):
        return sum(_token_count(item) for item in value)
    return 1


def dtype_from_name(name: str) -> torch.dtype:
    table = {
        "bf16": torch.bfloat16,
        "bfloat16": torch.bfloat16,
        "fp16": torch.float16,
        "float16": torch.float16,
        "fp32": torch.float32,
        "float32": torch.float32,
    }
    try:
        return table[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported dtype: {name}") from exc


def resolve_device(device: str) -> torch.device:
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    resolved = torch.device(device)
    if resolved.type == "cuda" and not torch.cuda.is_available():
        return torch.device("cpu")
    return resolved


def _is_likely_video_path(path: str) -> bool:
    return Path(path.split("?", 1)[0]).suffix.lower() in VIDEO_EXTENSIONS


def load_audio_av(audio: str, sampling_rate: int) -> np.ndarray:
    """Decode an audio stream from a media container with PyAV."""
    try:
        import av
    except ImportError as exc:
        raise ImportError("Install `av` to decode audio from video containers.") from exc

    chunks: list[np.ndarray] = []
    with av.open(audio) as container:
        stream = next((stream for stream in container.streams if stream.type == "audio"), None)
        if stream is None:
            raise ValueError(f"No audio stream found in {audio!r}.")

        resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=sampling_rate)
        for frame in container.decode(stream):
            frames = resampler.resample(frame)
            if frames is None:
                continue
            if not isinstance(frames, list):
                frames = [frames]
            for resampled in frames:
                chunks.append(resampled.to_ndarray().reshape(-1))

        frames = resampler.resample(None)
        if frames is not None:
            if not isinstance(frames, list):
                frames = [frames]
            for resampled in frames:
                chunks.append(resampled.to_ndarray().reshape(-1))

    if not chunks:
        raise ValueError(f"No decodable audio samples found in {audio!r}.")
    return (np.concatenate(chunks).astype(np.float32) / 32768.0).astype(np.float32, copy=False)


def load_audio_item(audio: str | np.ndarray, sampling_rate: int) -> np.ndarray:
    """Load audio with Transformers' loader, using PyAV for media containers."""
    if isinstance(audio, str) and _is_likely_video_path(audio):
        return load_audio_av(audio, sampling_rate=sampling_rate)
    try:
        return load_audio(audio, sampling_rate=sampling_rate)
    except Exception as exc:
        if not isinstance(audio, str):
            raise
        try:
            return load_audio_av(audio, sampling_rate=sampling_rate)
        except Exception as av_exc:
            raise RuntimeError(
                f"Failed to load audio {audio!r} with transformers.audio_utils.load_audio or PyAV."
            ) from av_exc


def process_audio_info(messages: list[dict[str, Any]], sampling_rate: int):
    """Load audio items from chat messages in the same order as the template."""
    audios = []
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            continue
        for item in content:
            if item.get("type") != "audio":
                continue
            audio = item.get("audio") or item.get("audio_url") or item.get("url") or item.get("path")
            if audio is None:
                raise ValueError("Audio content must include audio, audio_url, url, or path.")
            audios.append(load_audio_item(audio, sampling_rate=sampling_rate))
    return audios


def build_transcription_messages(audio_path: str | Path, prompt: str = DEFAULT_PROMPT) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "audio", "audio": str(audio_path)},
                {"type": "text", "text": prompt.strip() or DEFAULT_PROMPT},
            ],
        }
    ]


def prepare_inputs(processor, messages, *, max_length: int = 131072, device: torch.device | None = None):
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    audios = process_audio_info(messages, sampling_rate=processor.feature_extractor.sampling_rate)
    audio_kwargs = {"device": str(device)} if device is not None and device.type == "cuda" else {}
    return processor(
        text=text,
        audio=audios,
        max_length=max_length,
        audio_kwargs=audio_kwargs,
        return_tensors="pt",
    )


def generate_transcription(
    model,
    processor,
    messages,
    *,
    max_length: int = 131072,
    max_new_tokens: int | None = None,
    do_sample: bool = False,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    device: torch.device | None = None,
    dtype: torch.dtype | None = None,
    input_callback: Callable[[int], None] | None = None,
    token_callback: TokenCallback | None = None,
) -> dict[str, Any]:
    device = device or next(model.parameters()).device
    dtype = dtype or next(model.parameters()).dtype
    context = (
        torch.amp.autocast("cuda", dtype=dtype)
        if device.type == "cuda" and dtype in (torch.float16, torch.bfloat16)
        else torch.no_grad()
    )
    with context:
        inputs = prepare_inputs(processor, messages, max_length=max_length, device=device).to(device)

    prompt_len = int(inputs["attention_mask"][0].sum().item())
    if input_callback is not None:
        input_callback(prompt_len)
    generation_config = copy.deepcopy(model.generation_config)
    if max_new_tokens is not None:
        generation_config.max_new_tokens = max_new_tokens
    generation_config.do_sample = do_sample
    if do_sample and temperature is not None:
        generation_config.temperature = temperature
    if do_sample and top_p is not None:
        generation_config.top_p = top_p
    if do_sample and top_k is not None:
        generation_config.top_k = top_k
    streamer = ProgressStreamer(token_callback) if token_callback is not None else None
    generate_kwargs = {
        "input_ids": inputs["input_ids"],
        "attention_mask": inputs["attention_mask"],
        "input_features": inputs["input_features"],
        "audio_feature_lengths": inputs["audio_feature_lengths"],
        "audio_chunk_mapping": inputs["audio_chunk_mapping"],
        "generation_config": generation_config,
    }
    if streamer is not None:
        generate_kwargs["streamer"] = streamer

    with torch.inference_mode(), (
        torch.amp.autocast("cuda", dtype=dtype)
        if device.type == "cuda" and dtype in (torch.float16, torch.bfloat16)
        else torch.no_grad()
    ):
        try:
            outputs = model.generate(**generate_kwargs)
        except TypeError as exc:
            if streamer is None or "streamer" not in str(exc):
                raise
            generate_kwargs.pop("streamer", None)
            outputs = model.generate(**generate_kwargs)

    generated_ids = outputs[0][prompt_len:]
    text = processor.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    return {
        "text": text,
        "prompt_len": prompt_len,
        "generated_tokens": int(generated_ids.numel()),
    }
