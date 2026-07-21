from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from transformers import AutoModelForCausalLM, AutoProcessor

from moss_transcribe_diarize.inference_utils import (
    DEFAULT_PROMPT,
    build_transcription_messages,
    dtype_from_name,
    generate_transcription,
    resolve_device,
)


StatusCallback = Callable[[str, float | None, int | None], None]


def generation_progress(generated_tokens: int, max_new_tokens: int | None) -> float:
    if not max_new_tokens or max_new_tokens <= 0:
        return 0.25
    ratio = max(0.0, min(1.0, generated_tokens / float(max_new_tokens)))
    return 0.25 + (0.85 - 0.25) * ratio


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    prompt_len: int
    generated_tokens: int
    elapsed_sec: float
    model: str
    audio: str
    decoding: str
    temperature: float | None
    top_p: float | None = None
    top_k: int | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "prompt_len": self.prompt_len,
            "generated_tokens": self.generated_tokens,
            "elapsed_sec": self.elapsed_sec,
            "model": self.model,
            "audio": self.audio,
            "decoding": self.decoding,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }


class ModelRunner:
    """Lazy, single-process model runner guarded by a GPU lock."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        device: str = "auto",
        dtype: str = "bf16",
    ):
        self.model_path = str(Path(model_path).expanduser())
        self.device_name = device
        self.dtype_name = dtype
        self._model = None
        self._processor = None
        self._device: torch.device | None = None
        self._dtype: torch.dtype | None = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._processor is not None

    def runtime_info(self) -> dict:
        return {
            "backend": "hf",
            "path": self.model_path,
            "device": self.device_name,
            "dtype": self.dtype_name,
        }

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        prompt: str = DEFAULT_PROMPT,
        max_length: int = 131072,
        max_new_tokens: int = 2048,
        decoding: str = "greedy",
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        status_callback: StatusCallback | None = None,
    ) -> TranscriptionResult:
        do_sample = decoding == "sample"
        with self._lock:
            if status_callback is not None:
                status_callback("loading_model", 0.05, None)
            self._ensure_loaded()
            if status_callback is not None:
                status_callback("transcribing", 0.10, None)

            def on_inputs_ready(prompt_len: int) -> None:
                if status_callback is not None:
                    status_callback("transcribing", 0.25, None)

            def on_generated_tokens(generated_tokens: int) -> None:
                if status_callback is not None:
                    status_callback("transcribing", generation_progress(generated_tokens, max_new_tokens), generated_tokens)

            started = time.time()
            result = generate_transcription(
                self._model,
                self._processor,
                build_transcription_messages(audio_path, prompt),
                max_length=max_length,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                top_p=top_p if do_sample else None,
                top_k=top_k if do_sample else None,
                device=self._device,
                dtype=self._dtype,
                input_callback=on_inputs_ready,
                token_callback=on_generated_tokens,
            )
            if status_callback is not None:
                status_callback("transcribing", 0.85, int(result["generated_tokens"]))
            return TranscriptionResult(
                text=result["text"],
                prompt_len=int(result["prompt_len"]),
                generated_tokens=int(result["generated_tokens"]),
                elapsed_sec=time.time() - started,
                model=self.model_path,
                audio=str(Path(audio_path).expanduser()),
                decoding=decoding,
                temperature=temperature if do_sample else None,
                top_p=top_p if do_sample else None,
                top_k=top_k if do_sample else None,
            )

    def _ensure_loaded(self) -> None:
        if self.is_loaded:
            return
        device = resolve_device(self.device_name)
        dtype = dtype_from_name(self.dtype_name)
        if device.type == "cpu":
            dtype = torch.float32
        model = AutoModelForCausalLM.from_pretrained(self.model_path, trust_remote_code=True, dtype="auto")
        processor = AutoProcessor.from_pretrained(self.model_path, trust_remote_code=True, fix_mistral_regex=True)
        self._model = model.to(dtype=dtype).to(device).eval()
        self._processor = processor
        self._device = device
        self._dtype = dtype
