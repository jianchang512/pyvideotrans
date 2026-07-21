from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import soundfile as sf

from moss_transcribe_diarize.inference_utils import DEFAULT_PROMPT, load_audio_item

from .model_runner import StatusCallback, TranscriptionResult, generation_progress


class VllmRunner:
    """Remote vLLM OpenAI-compatible audio transcription runner."""

    device_name = "vllm-api"
    dtype_name = "remote"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 600.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_path = model
        self.api_key = api_key or "EMPTY"
        self.timeout = timeout

    @property
    def is_loaded(self) -> bool:
        return True

    def runtime_info(self) -> dict:
        return {
            "backend": "vllm",
            "path": self.model_path,
            "device": self.device_name,
            "dtype": self.dtype_name,
            "base_url": self.base_url,
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
        status_callback: StatusCallback | None = None,
    ) -> TranscriptionResult:
        del max_length
        started = time.time()
        if status_callback is not None:
            status_callback("loading_model", 0.05, None)
        wav_bytes = _media_to_wav_bytes(audio_path)
        if status_callback is not None:
            status_callback("transcribing", 0.25, None)

        fields = self._build_fields(
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            decoding=decoding,
            temperature=temperature,
        )
        response = self._post_multipart(
            self._transcriptions_url(),
            fields=fields,
            file_field="file",
            filename="audio.wav",
            content_type="audio/wav",
            file_bytes=wav_bytes,
            status_callback=status_callback,
            max_new_tokens=max_new_tokens,
        )
        text = _extract_transcription_text(response)
        usage = response.get("usage") or {}
        generated_tokens = int(usage.get("completion_tokens") or 0)
        prompt_len = int(usage.get("prompt_tokens") or 0)
        if status_callback is not None:
            status_callback("transcribing", 0.85, generated_tokens)
        return TranscriptionResult(
            text=text,
            prompt_len=prompt_len,
            generated_tokens=generated_tokens,
            elapsed_sec=time.time() - started,
            model=self.model_path,
            audio=str(Path(audio_path).expanduser()),
            decoding=decoding,
            temperature=temperature if decoding == "sample" else None,
        )

    def _build_fields(
        self,
        *,
        prompt: str,
        max_new_tokens: int,
        decoding: str,
        temperature: float | None,
    ) -> dict[str, str]:
        return {
            "model": self.model_path,
            "prompt": prompt.strip() or DEFAULT_PROMPT,
            "response_format": "json",
            "stream": "true",
            "stream_include_usage": "true",
            "stream_continuous_usage_stats": "true",
            "max_completion_tokens": str(int(max_new_tokens)),
            "temperature": str(float(temperature if decoding == "sample" and temperature is not None else 0.0)),
        }

    def _transcriptions_url(self) -> str:
        if self.base_url.endswith("/audio/transcriptions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return self.base_url + "/audio/transcriptions"
        return self.base_url + "/v1/audio/transcriptions"

    def _post_multipart(
        self,
        url: str,
        *,
        fields: dict[str, str],
        file_field: str,
        filename: str,
        content_type: str,
        file_bytes: bytes,
        status_callback: StatusCallback | None = None,
        max_new_tokens: int | None = None,
    ) -> dict[str, Any]:
        boundary = f"----mtd-{uuid.uuid4().hex}"
        body = _multipart_body(
            boundary=boundary,
            fields=fields,
            file_field=file_field,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
        )
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content_type_header = response.headers.get("Content-Type", "")
                if "text/event-stream" in content_type_header:
                    return _consume_sse_transcription(
                        response,
                        status_callback=status_callback,
                        max_new_tokens=max_new_tokens,
                    )
                raw = response.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"text": raw}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"vLLM request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to connect to vLLM API: {exc.reason}") from exc


def _media_to_wav_bytes(path: str | Path) -> bytes:
    path = Path(path).expanduser()
    audio = load_audio_item(str(path), sampling_rate=16000)
    buffer = io.BytesIO()
    sf.write(buffer, audio, 16000, format="WAV")
    return buffer.getvalue()


def _multipart_body(
    *,
    boundary: str,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks)


def _extract_transcription_text(response: dict[str, Any]) -> str:
    content = response.get("text")
    if isinstance(content, str):
        return content.strip()
    return ""


def _consume_sse_transcription(
    response: Any,
    *,
    status_callback: StatusCallback | None,
    max_new_tokens: int | None,
) -> dict[str, Any]:
    parts: list[str] = []
    usage: dict[str, int] = {}

    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        chunk = json.loads(data)

        chunk_usage = chunk.get("usage")
        if isinstance(chunk_usage, dict):
            prompt_tokens = chunk_usage.get("prompt_tokens")
            completion_tokens = chunk_usage.get("completion_tokens")
            if isinstance(prompt_tokens, int):
                usage["prompt_tokens"] = prompt_tokens
            if isinstance(completion_tokens, int):
                usage["completion_tokens"] = completion_tokens
                if status_callback is not None:
                    status_callback(
                        "transcribing",
                        generation_progress(completion_tokens, max_new_tokens),
                        completion_tokens,
                    )

        for choice in chunk.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta") or {}
            if not isinstance(delta, dict):
                continue
            content = delta.get("content")
            if isinstance(content, str) and content:
                parts.append(content)

    return {"text": "".join(parts), "usage": usage}
