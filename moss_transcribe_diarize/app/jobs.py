from __future__ import annotations

import json
import queue
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from moss_transcribe_diarize.subtitle import (
    SubtitleSegment,
    SubtitleStyle,
    coerce_subtitle_segments,
    export_ass,
    export_json,
    export_srt,
    subtitle_segments_from_transcript,
    write_text,
)

from .ffmpeg import burn_ass_subtitles, detect_ffmpeg, probe_video_size
from .model_runner import ModelRunner


TERMINAL_STATES = {"waiting_review", "done", "failed", "cancelled"}


@dataclass(slots=True)
class JobRecord:
    id: str
    status: str
    media_name: str
    input_path: str
    job_dir: str
    inference_prompt: str
    max_length: int
    max_new_tokens: int
    decoding: str
    temperature: float | None
    progress: float = 0.0
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    model: str | None = None
    prompt_len: int | None = None
    generated_tokens: int | None = None
    elapsed_sec: float | None = None
    subtitle_style: dict[str, Any] = field(default_factory=dict)

    @property
    def raw_transcript_path(self) -> Path:
        return Path(self.job_dir) / "raw_transcript.txt"

    @property
    def segments_path(self) -> Path:
        return Path(self.job_dir) / "segments.json"

    @property
    def srt_path(self) -> Path:
        return Path(self.job_dir) / "subtitle.srt"

    @property
    def ass_path(self) -> Path:
        return Path(self.job_dir) / "subtitle.ass"

    @property
    def output_path(self) -> Path:
        return Path(self.job_dir) / "output.mp4"

    @property
    def job_path(self) -> Path:
        return Path(self.job_dir) / "job.json"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        possibly_truncated = (
            self.generated_tokens is not None
            and self.max_new_tokens > 0
            and self.generated_tokens >= self.max_new_tokens
        )
        data["inference"] = {
            "prompt": self.inference_prompt,
            "max_length": self.max_length,
            "max_new_tokens": self.max_new_tokens,
            "decoding": self.decoding,
            "temperature": self.temperature,
        }
        data["usage"] = {
            "prompt_tokens": self.prompt_len,
            "generated_tokens": self.generated_tokens,
            "max_new_tokens": self.max_new_tokens,
            "possibly_truncated": possibly_truncated,
            "elapsed_sec": self.elapsed_sec,
        }
        data["files"] = {
            "raw_transcript": str(self.raw_transcript_path),
            "segments": str(self.segments_path),
            "srt": str(self.srt_path),
            "ass": str(self.ass_path),
            "mp4": str(self.output_path),
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRecord":
        inference = data.get("inference") or {}
        temperature = data.get("temperature", inference.get("temperature"))
        return cls(
            id=str(data["id"]),
            status=str(data.get("status") or "failed"),
            media_name=str(data.get("media_name") or "input.media"),
            input_path=str(data.get("input_path") or ""),
            job_dir=str(data.get("job_dir") or ""),
            inference_prompt=str(data.get("inference_prompt") or inference.get("prompt") or ""),
            max_length=int(data.get("max_length") or inference.get("max_length") or 0),
            max_new_tokens=int(data.get("max_new_tokens") or inference.get("max_new_tokens") or 0),
            decoding=str(data.get("decoding") or inference.get("decoding") or "greedy"),
            temperature=None if temperature is None else float(temperature),
            progress=float(data.get("progress") or 0.0),
            error=data.get("error"),
            created_at=float(data.get("created_at") or time.time()),
            updated_at=float(data.get("updated_at") or time.time()),
            model=data.get("model"),
            prompt_len=data.get("prompt_len"),
            generated_tokens=data.get("generated_tokens"),
            elapsed_sec=data.get("elapsed_sec"),
            subtitle_style=dict(data.get("subtitle_style") or {}),
        )


class JobManager:
    def __init__(
        self,
        runs_dir: str | Path,
        model_runner: ModelRunner,
        *,
        prompt: str,
        max_length: int,
        max_new_tokens: int,
        decoding: str = "greedy",
        temperature: float | None = None,
    ):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.model_runner = model_runner
        self.prompt = prompt
        self.max_length = max_length
        self.max_new_tokens = max_new_tokens
        self.decoding = decoding
        self.temperature = temperature
        self._jobs: dict[str, JobRecord] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._render_lock = threading.Lock()
        self._progress_save_times: dict[str, float] = {}
        self._load_existing_jobs()
        self._worker = threading.Thread(target=self._worker_loop, name="mtd-job-worker", daemon=True)
        self._worker.start()

    def create_job_from_file(
        self,
        source_path: str | Path,
        media_name: str | None = None,
        *,
        prompt: str | None = None,
        max_length: int | None = None,
        max_new_tokens: int | None = None,
        decoding: str | None = None,
        temperature: float | None = None,
    ) -> JobRecord:
        options = self._resolve_inference_options(
            prompt=prompt,
            max_length=max_length,
            max_new_tokens=max_new_tokens,
            decoding=decoding,
            temperature=temperature,
        )
        job_id = uuid.uuid4().hex[:12]
        source_path = Path(source_path)
        suffix = source_path.suffix or ".media"
        job_dir = self.runs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        input_path = job_dir / f"input{suffix}"
        shutil.copyfile(source_path, input_path)
        job = JobRecord(
            id=job_id,
            status="queued",
            progress=0.0,
            media_name=media_name or source_path.name,
            input_path=str(input_path),
            job_dir=str(job_dir),
            inference_prompt=options["prompt"],
            max_length=options["max_length"],
            max_new_tokens=options["max_new_tokens"],
            decoding=options["decoding"],
            temperature=options["temperature"],
            model=self.model_runner.model_path,
        )
        self._jobs[job.id] = job
        self._save_job(job)
        self._queue.put(job.id)
        return job

    def create_job_for_upload(
        self,
        filename: str,
        *,
        prompt: str | None = None,
        max_length: int | None = None,
        max_new_tokens: int | None = None,
        decoding: str | None = None,
        temperature: float | None = None,
    ) -> tuple[JobRecord, Path]:
        options = self._resolve_inference_options(
            prompt=prompt,
            max_length=max_length,
            max_new_tokens=max_new_tokens,
            decoding=decoding,
            temperature=temperature,
        )
        job_id = uuid.uuid4().hex[:12]
        suffix = Path(filename).suffix or ".media"
        job_dir = self.runs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        input_path = job_dir / f"input{suffix}"
        job = JobRecord(
            id=job_id,
            status="queued",
            progress=0.0,
            media_name=filename,
            input_path=str(input_path),
            job_dir=str(job_dir),
            inference_prompt=options["prompt"],
            max_length=options["max_length"],
            max_new_tokens=options["max_new_tokens"],
            decoding=options["decoding"],
            temperature=options["temperature"],
            model=self.model_runner.model_path,
        )
        self._jobs[job.id] = job
        self._save_job(job)
        return job, input_path

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def rerun_job(
        self,
        job_id: str,
        *,
        prompt: str | None = None,
        max_length: int | None = None,
        max_new_tokens: int | None = None,
        decoding: str | None = None,
        temperature: float | None = None,
    ) -> JobRecord:
        source = self.get_job(job_id)
        input_path = Path(source.input_path)
        if not input_path.exists():
            raise FileNotFoundError(str(input_path))
        return self.create_job_from_file(
            input_path,
            media_name=source.media_name,
            prompt=source.inference_prompt if prompt is None else prompt,
            max_length=source.max_length if max_length is None else max_length,
            max_new_tokens=source.max_new_tokens if max_new_tokens is None else max_new_tokens,
            decoding=source.decoding if decoding is None else decoding,
            temperature=source.temperature if temperature is None else temperature,
        )

    def list_jobs(self) -> list[JobRecord]:
        return sorted(self._jobs.values(), key=lambda job: job.updated_at, reverse=True)

    def get_job(self, job_id: str) -> JobRecord:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc

    def delete_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job.status in {"queued", "loading_model", "transcribing", "postprocessing", "rendering"}:
            raise RuntimeError("Cannot delete a job while it is running.")
        self._jobs.pop(job_id, None)
        shutil.rmtree(job.job_dir, ignore_errors=True)

    def list_segments(self, job_id: str) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        if not job.segments_path.exists():
            return []
        return json.loads(job.segments_path.read_text(encoding="utf-8"))

    def update_segments(
        self,
        job_id: str,
        payload: list[dict[str, Any]],
        style_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        segments = coerce_subtitle_segments(payload)
        style = SubtitleStyle.from_dict(style_payload) if style_payload is not None else None
        if style is not None:
            job.subtitle_style = style.to_dict()
        self._write_subtitle_files(job, segments, style=style)
        if job.status == "done":
            self._set_status(job, "waiting_review", 0.95, error=None)
        else:
            self._touch(job, error=None)
        return [segment.to_dict() for segment in segments]

    def render(self, job_id: str, style_payload: dict[str, Any] | None = None) -> JobRecord:
        job = self.get_job(job_id)
        if not detect_ffmpeg().available:
            raise RuntimeError("ffmpeg and ffprobe are not available on PATH.")
        if not job.segments_path.exists():
            raise RuntimeError("No subtitle segments are available for this job.")
        threading.Thread(
            target=self._render_job,
            args=(job.id, SubtitleStyle.from_dict(style_payload)),
            name=f"mtd-render-{job.id}",
            daemon=True,
        ).start()
        return job

    def download_path(self, job_id: str, kind: str) -> Path:
        job = self.get_job(job_id)
        table = {
            "json": job.segments_path,
            "segments": job.segments_path,
            "srt": job.srt_path,
            "ass": job.ass_path,
            "mp4": job.output_path,
            "transcript": job.raw_transcript_path,
        }
        if kind not in table:
            raise KeyError(f"Unsupported download kind: {kind}")
        path = table[kind]
        if not path.exists():
            raise FileNotFoundError(str(path))
        return path

    def _worker_loop(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._process_job(self.get_job(job_id))
            finally:
                self._queue.task_done()

    def _load_existing_jobs(self) -> None:
        for path in sorted(self.runs_dir.glob("*/job.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job = JobRecord.from_dict(data)
                if not job.job_dir:
                    job.job_dir = str(path.parent)
                if job.status in {"queued", "loading_model", "transcribing", "postprocessing", "rendering"}:
                    job.status = "failed"
                    job.progress = 1.0
                    job.error = "Interrupted by previous server shutdown."
                    job.updated_at = time.time()
                    self._save_job(job)
                self._jobs[job.id] = job
            except Exception:
                continue

    def _process_job(self, job: JobRecord) -> None:
        try:
            def update(status: str, progress: float | None, generated_tokens: int | None = None) -> None:
                if status == "transcribing" and job.generated_tokens is None:
                    job.generated_tokens = 0
                if generated_tokens is not None:
                    job.generated_tokens = generated_tokens
                save = generated_tokens is None or self._should_save_live_progress(job.id)
                self._set_status(job, status, progress if progress is not None else job.progress, save=save)

            result = self.model_runner.transcribe(
                job.input_path,
                prompt=job.inference_prompt,
                max_length=job.max_length,
                max_new_tokens=job.max_new_tokens,
                decoding=job.decoding,
                temperature=job.temperature,
                status_callback=update,
            )
            job.generated_tokens = result.generated_tokens
            self._set_status(job, "postprocessing", 0.85, error=None)
            job.raw_transcript_path.write_text(result.text, encoding="utf-8")
            segments = subtitle_segments_from_transcript(result.text, postprocess=False)
            self._write_subtitle_files(job, segments)
            job.prompt_len = result.prompt_len
            job.elapsed_sec = result.elapsed_sec
            self._set_status(job, "waiting_review", 0.95, error=None)
            self._progress_save_times.pop(job.id, None)
        except Exception as exc:
            self._set_status(job, "failed", 1.0, error=str(exc))
            self._progress_save_times.pop(job.id, None)

    def _render_job(self, job_id: str, style: SubtitleStyle) -> None:
        job = self.get_job(job_id)
        with self._render_lock:
            try:
                self._set_status(job, "rendering", 0.97, error=None)
                segments = [SubtitleSegment.from_dict(item) for item in self.list_segments(job.id)]
                width, height = probe_video_size(job.input_path)
                write_text(job.ass_path, export_ass(segments, style=style, video_width=width, video_height=height))
                burn_ass_subtitles(job.input_path, job.ass_path, job.output_path)
                self._set_status(job, "done", 1.0, error=None)
            except Exception as exc:
                self._set_status(job, "waiting_review", 0.95, error=f"Render failed: {exc}")

    def _write_subtitle_files(
        self,
        job: JobRecord,
        segments: list[SubtitleSegment],
        *,
        style: SubtitleStyle | None = None,
    ) -> None:
        write_text(job.segments_path, export_json(segments))
        if style is None:
            style = SubtitleStyle.from_dict(job.subtitle_style) if job.subtitle_style else SubtitleStyle(font_size=48)
        write_text(
            job.srt_path,
            export_srt(segments, show_speaker=style.show_speaker, speaker_names=style.speaker_names),
            encoding="utf-8-sig",
        )
        width, height = probe_video_size(job.input_path)
        write_text(
            job.ass_path,
            export_ass(segments, style=style, video_width=width, video_height=height),
            encoding="utf-8-sig",
        )

    def _set_status(
        self,
        job: JobRecord,
        status: str,
        progress: float,
        *,
        error: str | None = None,
        save: bool = True,
    ) -> None:
        job.status = status
        job.progress = max(0.0, min(1.0, progress))
        self._touch(job, error=error, save=save)

    def _resolve_inference_options(
        self,
        *,
        prompt: str | None,
        max_length: int | None,
        max_new_tokens: int | None,
        decoding: str | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        prompt_value = self.prompt if prompt is None or not prompt.strip() else prompt
        max_length_value = self.max_length if max_length is None else int(max_length)
        max_new_tokens_value = self.max_new_tokens if max_new_tokens is None else int(max_new_tokens)
        decoding_value = decoding or self.decoding
        if decoding_value not in {"greedy", "sample"}:
            raise ValueError("decoding must be greedy or sample.")
        if max_length_value <= 0:
            raise ValueError("max_length must be greater than 0.")
        if max_new_tokens_value <= 0:
            raise ValueError("max_new_tokens must be greater than 0.")

        temperature_value = self.temperature if temperature is None else float(temperature)
        if decoding_value == "greedy":
            temperature_value = None
        else:
            if temperature_value is None:
                temperature_value = 1.0
            if temperature_value <= 0:
                raise ValueError("temperature must be greater than 0.")

        return {
            "prompt": prompt_value,
            "max_length": max_length_value,
            "max_new_tokens": max_new_tokens_value,
            "decoding": decoding_value,
            "temperature": temperature_value,
        }

    def _touch(self, job: JobRecord, *, error: str | None = None, save: bool = True) -> None:
        job.error = error
        job.updated_at = time.time()
        if save:
            self._save_job(job)

    def _save_job(self, job: JobRecord) -> None:
        job.job_path.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _should_save_live_progress(self, job_id: str) -> bool:
        now = time.time()
        last_saved = self._progress_save_times.get(job_id, 0.0)
        if now - last_saved < 0.5:
            return False
        self._progress_save_times[job_id] = now
        return True
