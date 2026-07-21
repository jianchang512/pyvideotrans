from __future__ import annotations

from collections.abc import Iterable

from moss_transcribe_diarize.transcript_parser import TranscriptSegment, parse_transcript

from .models import SubtitleSegment


DEFAULT_MIN_DURATION = 1.0
DEFAULT_MAX_DURATION = 6.0
DEFAULT_MAX_CHARS = 24
DEFAULT_MERGE_GAP = 0.3
PUNCTUATION = "。！？!?；;，,、 "


def subtitle_segments_from_transcript(
    transcript: str,
    *,
    postprocess: bool = True,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    max_chars: int = DEFAULT_MAX_CHARS,
    merge_gap: float = DEFAULT_MERGE_GAP,
) -> list[SubtitleSegment]:
    return subtitle_segments_from_transcript_segments(
        parse_transcript(transcript),
        postprocess=postprocess,
        min_duration=min_duration,
        max_duration=max_duration,
        max_chars=max_chars,
        merge_gap=merge_gap,
    )


def subtitle_segments_from_transcript_segments(
    segments: Iterable[TranscriptSegment],
    *,
    postprocess: bool = True,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    max_chars: int = DEFAULT_MAX_CHARS,
    merge_gap: float = DEFAULT_MERGE_GAP,
) -> list[SubtitleSegment]:
    subtitle_segments = [
        SubtitleSegment(
            id=f"seg_{index:04d}",
            start=float(segment.start),
            end=float(segment.end),
            speaker=segment.speaker,
            text=segment.text,
        )
        for index, segment in enumerate(segments, start=1)
    ]
    if not postprocess:
        return subtitle_segments
    return normalize_segments(
        subtitle_segments,
        min_duration=min_duration,
        max_duration=max_duration,
        max_chars=max_chars,
        merge_gap=merge_gap,
        regenerate_ids=True,
    )


def coerce_subtitle_segments(segments: Iterable[SubtitleSegment | dict]) -> list[SubtitleSegment]:
    """Convert user/API payloads to subtitle segments without timing edits."""
    coerced: list[SubtitleSegment] = []
    for index, item in enumerate(segments, start=1):
        segment = item if isinstance(item, SubtitleSegment) else SubtitleSegment.from_dict(item, fallback_id=f"seg_{index:04d}")
        coerced.append(
            SubtitleSegment(
                id=segment.id or f"seg_{index:04d}",
                start=float(segment.start),
                end=float(segment.end),
                speaker=segment.speaker or "S00",
                text=segment.text,
            )
        )
    return coerced


def normalize_segments(
    segments: Iterable[SubtitleSegment | dict],
    *,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    max_chars: int = DEFAULT_MAX_CHARS,
    merge_gap: float = DEFAULT_MERGE_GAP,
    regenerate_ids: bool = False,
) -> list[SubtitleSegment]:
    prepared = _prepare_segments(segments)
    prepared = _fix_overlaps(prepared, min_duration=min_duration)
    prepared = _merge_adjacent(prepared, merge_gap=merge_gap, max_chars=max_chars)
    prepared = _split_long_segments(
        prepared,
        min_duration=min_duration,
        max_duration=max_duration,
        max_chars=max_chars,
    )
    prepared = _fix_overlaps(prepared, min_duration=min_duration)
    if regenerate_ids:
        for index, segment in enumerate(prepared, start=1):
            segment.id = f"seg_{index:04d}"
    return prepared


def _prepare_segments(segments: Iterable[SubtitleSegment | dict]) -> list[SubtitleSegment]:
    prepared: list[SubtitleSegment] = []
    for index, item in enumerate(segments, start=1):
        segment = item if isinstance(item, SubtitleSegment) else SubtitleSegment.from_dict(item, fallback_id=f"seg_{index:04d}")
        text = segment.text.strip()
        if not text:
            continue
        start = max(0.0, float(segment.start))
        end = max(start, float(segment.end))
        prepared.append(
            SubtitleSegment(
                id=segment.id or f"seg_{index:04d}",
                start=start,
                end=end,
                speaker=segment.speaker or "S00",
                text=text,
            )
        )
    prepared.sort(key=lambda segment: (segment.start, segment.end))
    return prepared


def _fix_overlaps(segments: list[SubtitleSegment], *, min_duration: float) -> list[SubtitleSegment]:
    cursor = 0.0
    fixed: list[SubtitleSegment] = []
    for segment in segments:
        start = max(segment.start, cursor)
        end = max(segment.end, start + min_duration)
        fixed.append(
            SubtitleSegment(
                id=segment.id,
                start=start,
                end=end,
                speaker=segment.speaker,
                text=segment.text,
            )
        )
        cursor = end
    return fixed


def _merge_adjacent(segments: list[SubtitleSegment], *, merge_gap: float, max_chars: int) -> list[SubtitleSegment]:
    if not segments:
        return []

    merged = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        gap = segment.start - previous.end
        combined_text = _join_text(previous.text, segment.text)
        can_merge = (
            previous.speaker == segment.speaker
            and 0 <= gap <= merge_gap
            and len(combined_text) <= max_chars * 2
        )
        if can_merge:
            merged[-1] = SubtitleSegment(
                id=previous.id,
                start=previous.start,
                end=max(previous.end, segment.end),
                speaker=previous.speaker,
                text=combined_text,
            )
        else:
            merged.append(segment)
    return merged


def _split_long_segments(
    segments: list[SubtitleSegment],
    *,
    min_duration: float,
    max_duration: float,
    max_chars: int,
) -> list[SubtitleSegment]:
    output: list[SubtitleSegment] = []
    for segment in segments:
        duration = segment.end - segment.start
        if duration <= max_duration and len(segment.text) <= max_chars:
            output.append(segment)
            continue

        chunks = _split_text(segment.text, max_chars=max_chars)
        if len(chunks) <= 1:
            output.append(segment)
            continue

        total_chars = sum(max(len(chunk), 1) for chunk in chunks)
        cursor = segment.start
        for index, chunk in enumerate(chunks):
            if index == len(chunks) - 1:
                end = segment.end
            else:
                ratio = max(len(chunk), 1) / total_chars
                end = cursor + max(min_duration, duration * ratio)
                end = min(end, segment.end - min_duration * (len(chunks) - index - 1))
            output.append(
                SubtitleSegment(
                    id=f"{segment.id}_{index + 1}",
                    start=cursor,
                    end=max(end, cursor + min_duration),
                    speaker=segment.speaker,
                    text=chunk,
                )
            )
            cursor = output[-1].end
    return output


def _split_text(text: str, *, max_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    for ch in text:
        current.append(ch)
        should_cut = len(current) >= max_chars or (ch in PUNCTUATION and len(current) >= max_chars // 2)
        if should_cut:
            chunks.append("".join(current).strip())
            current.clear()
    if current:
        chunks.append("".join(current).strip())

    compact: list[str] = []
    for chunk in chunks:
        if not chunk:
            continue
        if compact and len(compact[-1]) + len(chunk) <= max_chars:
            compact[-1] = _join_text(compact[-1], chunk)
        else:
            compact.append(chunk)
    return compact


def _join_text(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and right[0].isascii():
        return f"{left} {right}"
    return f"{left}{right}"
