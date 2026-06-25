# -*- coding: utf-8 -*-
"""
TwelveLabs content-aware video understanding.

An opt-in helper that uses TwelveLabs' Pegasus model to generate a natural
language description / summary of a video (what happens in it, scene
breakdown, key topics, etc.) before or alongside the usual
transcribe -> translate -> dub workflow. It also exposes a Marengo
multimodal text embedding helper that can be used for semantic search.

This module has no effect on existing behaviour: nothing imports it unless
the user explicitly runs the `analyze` task. The `twelvelabs` SDK is an
optional dependency and is imported lazily so the rest of pyVideoTrans keeps
working when it is not installed.

Get a free API key (generous free tier) at https://twelvelabs.io
"""
import base64
import os
from pathlib import Path
from typing import List

from videotrans.configure.config import params, logger

# Pegasus video understanding model and Marengo embedding model.
PEGASUS_MODEL = "pegasus1.5"
MARENGO_MODEL = "marengo3.0"

# Videos sent inline (base64) must be <= 1 hour and within Pegasus limits.
# Larger files should be pre-segmented before calling analyze().
DEFAULT_PROMPT = (
    "Describe this video in detail: summarize what happens, list the main "
    "topics and any on-screen text, and note the overall tone."
)


def _get_api_key() -> str:
    """Read the TwelveLabs key from saved settings, falling back to env."""
    key = (params.get("twelvelabs_key", "") or "").strip()
    if not key:
        key = (os.environ.get("TWELVELABS_API_KEY", "") or "").strip()
    return key


def _make_client():
    """Lazily import the SDK and build a client, or raise a clear error."""
    try:
        from twelvelabs import TwelveLabs
    except ImportError as e:
        raise RuntimeError(
            "The 'twelvelabs' package is required for TwelveLabs analysis. "
            "Install it with: uv sync --extra twelvelabs"
        ) from e

    key = _get_api_key()
    if not key:
        raise RuntimeError(
            "TwelveLabs API key not configured. Set 'twelvelabs_key' in "
            "settings or the TWELVELABS_API_KEY environment variable. "
            "Get a free key at https://twelvelabs.io"
        )
    return TwelveLabs(api_key=key)


def analyze_video(
    video_path: str,
    prompt: str = DEFAULT_PROMPT,
    max_tokens: int = 2048,
) -> str:
    """Run Pegasus over a local video file and return the generated text.

    The file is sent inline as base64, so no index/upload step is needed.
    Suitable for clips up to ~1 hour; segment longer videos first.
    """
    from twelvelabs.types import VideoContext_Base64String

    p = Path(video_path)
    if not p.exists():
        raise FileNotFoundError(video_path)

    client = _make_client()
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")

    logger.info(f"TwelveLabs Pegasus analyzing {p.name} (prompt={prompt!r})")
    resp = client.analyze(
        model_name=PEGASUS_MODEL,
        video=VideoContext_Base64String(base_64_string=b64),
        prompt=prompt,
        max_tokens=max_tokens,
    )
    return resp.data or ""


def embed_text(text: str) -> List[float]:
    """Return the 512-dim Marengo embedding for a text query.

    Useful for semantic search over content analyzed with Pegasus.
    """
    client = _make_client()
    resp = client.embed.create(model_name=MARENGO_MODEL, text=text)
    segments = (resp.text_embedding.segments if resp.text_embedding else None) or []
    if not segments or not segments[0].float_:
        raise RuntimeError("TwelveLabs returned no embedding")
    return segments[0].float_


if __name__ == "__main__":
    # ponytail: no-network self-check — verifies key/SDK wiring without a video.
    # A real embedding call runs only when TWELVELABS_API_KEY is set.
    import sys

    if os.environ.get("TWELVELABS_API_KEY"):
        vec = embed_text("a person walking a dog")
        assert len(vec) == 512, f"expected 512-dim, got {len(vec)}"
        print(f"OK: Marengo embedding dim={len(vec)}")
    else:
        # Missing key must raise a clear, actionable error.
        try:
            _make_client()
        except RuntimeError as e:
            assert "API key" in str(e) or "twelvelabs" in str(e).lower()
            print("OK: missing-key path raises clear error")
            sys.exit(0)
