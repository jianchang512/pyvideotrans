from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from moss_transcribe_diarize.inference_utils import DEFAULT_PROMPT
from moss_transcribe_diarize.subtitle import (
    export_ass,
    export_json,
    export_srt,
    subtitle_segments_from_transcript,
    write_text,
)

from .ffmpeg import burn_ass_subtitles, detect_ffmpeg, probe_video_size
from .model_runner import ModelRunner
from .vllm_runner import VllmRunner


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "pretrained" / "moss-transcribe-diarize"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate editable subtitles and optionally burn them into video.")
    parser.add_argument("input", help="Input audio or video path.")
    parser.add_argument("--backend", choices=["hf", "vllm"], default="hf")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--vllm-base-url", default=None, help="OpenAI-compatible vLLM base URL, e.g. http://127.0.0.1:8000/v1.")
    parser.add_argument("--vllm-model", default=None, help="vLLM served model name. Defaults to --model.")
    parser.add_argument("--vllm-api-key", default="EMPTY")
    parser.add_argument("--vllm-timeout", type=float, default=600.0)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", default="bf16")
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--max-len", type=int, default=131072)
    parser.add_argument("--decoding", choices=["greedy", "sample"], default="greedy")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--render", action="store_true", help="Burn subtitle.ass into output.mp4 with FFmpeg.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser()
    out_dir = Path(args.out_dir or f"runs/cli_{time.strftime('%Y%m%d_%H%M%S')}").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.backend == "vllm":
        if not args.vllm_base_url:
            raise SystemExit("--vllm-base-url is required when --backend vllm.")
        runner = VllmRunner(
            base_url=args.vllm_base_url,
            model=args.vllm_model or args.model,
            api_key=args.vllm_api_key,
            timeout=args.vllm_timeout,
        )
    else:
        runner = ModelRunner(args.model, device=args.device, dtype=args.dtype)
    result = runner.transcribe(
        input_path,
        prompt=args.prompt,
        max_length=args.max_len,
        max_new_tokens=args.max_new_tokens,
        decoding=args.decoding,
        temperature=args.temperature,
    )
    segments = subtitle_segments_from_transcript(result.text, postprocess=False)

    raw_transcript = write_text(out_dir / "raw_transcript.txt", result.text)
    segments_path = write_text(out_dir / "segments.json", export_json(segments))
    srt_path = write_text(out_dir / "subtitle.srt", export_srt(segments, show_speaker=True), encoding="utf-8-sig")
    width, height = probe_video_size(input_path)
    ass_path = write_text(out_dir / "subtitle.ass", export_ass(segments, video_width=width, video_height=height), encoding="utf-8-sig")

    output_path = None
    if args.render:
        if not detect_ffmpeg().available:
            raise SystemExit("ffmpeg and ffprobe are required for --render.")
        output_path = burn_ass_subtitles(input_path, ass_path, out_dir / "output.mp4")

    summary = {
        "input": str(input_path),
        "out_dir": str(out_dir),
        "segments": len(segments),
        "files": {
            "raw_transcript": str(raw_transcript),
            "segments": str(segments_path),
            "srt": str(srt_path),
            "ass": str(ass_path),
            "mp4": str(output_path) if output_path else None,
        },
        "transcription": {k: v for k, v in result.to_dict().items() if k != "text"},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
