from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FFmpegAvailability:
    ffmpeg: str | None
    ffprobe: str | None

    @property
    def available(self) -> bool:
        return bool(self.ffmpeg and self.ffprobe)

    def to_dict(self) -> dict[str, str | bool | None]:
        return {"available": self.available, "ffmpeg": self.ffmpeg, "ffprobe": self.ffprobe}


def detect_ffmpeg() -> FFmpegAvailability:
    return FFmpegAvailability(ffmpeg=shutil.which("ffmpeg"), ffprobe=shutil.which("ffprobe"))


def probe_media(path: str | Path) -> dict[str, Any]:
    tools = detect_ffmpeg()
    if not tools.ffprobe:
        raise RuntimeError("ffprobe is not available on PATH.")
    command = [
        tools.ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout or "{}")


def probe_video_size(path: str | Path, *, default: tuple[int, int] = (1920, 1080)) -> tuple[int, int]:
    try:
        media = probe_media(path)
    except Exception:
        return default
    for stream in media.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width") or default[0])
            height = int(stream.get("height") or default[1])
            return width, height
    return default


def burn_ass_subtitles(
    input_media: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = True,
) -> Path:
    tools = detect_ffmpeg()
    if not tools.available:
        raise RuntimeError("ffmpeg and ffprobe are required for video rendering.")

    input_media = Path(input_media).resolve()
    ass_path = Path(ass_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        tools.ffmpeg or "ffmpeg",
        "-y" if overwrite else "-n",
        "-i",
        str(input_media),
        "-vf",
        f"subtitles={ass_path.name}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, cwd=str(ass_path.parent), check=True, capture_output=True, text=True)
    return output_path
