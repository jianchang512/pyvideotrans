"""
Tests for videotrans.util.twelvelabs_analyze — the opt-in TwelveLabs
content-aware video understanding helper.

The no-network tests mock the twelvelabs SDK so they run without the package
installed or any API key. The live test is skipped unless TWELVELABS_API_KEY
is set, mirroring how the project gates other network-dependent checks.

Uses conftest.py mocks for heavy dependencies.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from videotrans.util import twelvelabs_analyze as tla


# ===========================================================================
# Module surface / constants
# ===========================================================================
def test_models_are_pinned():
    assert tla.PEGASUS_MODEL == "pegasus1.5"
    assert tla.MARENGO_MODEL == "marengo3.0"


def test_default_prompt_is_nonempty():
    assert isinstance(tla.DEFAULT_PROMPT, str) and tla.DEFAULT_PROMPT.strip()


def test_cli_registers_analyze_task():
    from cli import build_parser, analyze_fun  # noqa: F401

    parser = build_parser()
    args = parser.parse_args(["--task", "analyze", "--name", "x.mp4",
                              "--tl_prompt", "hi", "--tl_max_tokens", "10"])
    assert args.task == "analyze"
    assert args.tl_prompt == "hi"
    assert args.tl_max_tokens == 10


# ===========================================================================
# Key resolution
# ===========================================================================
def test_get_api_key_prefers_params(monkeypatch):
    monkeypatch.setattr(tla.params, "get", lambda k, d="": "from_params" if k == "twelvelabs_key" else d)
    assert tla._get_api_key() == "from_params"


def test_get_api_key_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(tla.params, "get", lambda k, d="": d)
    monkeypatch.setenv("TWELVELABS_API_KEY", "from_env")
    assert tla._get_api_key() == "from_env"


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(tla.params, "get", lambda k, d="": d)
    monkeypatch.delenv("TWELVELABS_API_KEY", raising=False)
    # Pretend the SDK is installed so we reach the key check, not the import error.
    with patch.dict(sys.modules, {"twelvelabs": MagicMock()}):
        with pytest.raises(RuntimeError, match="API key"):
            tla._make_client()


# ===========================================================================
# No-network wiring tests (SDK mocked)
# ===========================================================================
def test_analyze_video_wiring(monkeypatch, tmp_path):
    monkeypatch.setattr(tla.params, "get", lambda k, d="": d)
    monkeypatch.setenv("TWELVELABS_API_KEY", "k")

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake-bytes")

    fake_client = MagicMock()
    fake_client.analyze.return_value = MagicMock(data="A dog runs in a park.")

    with patch.object(tla, "_make_client", return_value=fake_client):
        # VideoContext_Base64String is imported inside the function from the SDK.
        with patch.dict(sys.modules, {"twelvelabs.types": MagicMock()}):
            out = tla.analyze_video(str(video), prompt="What happens?", max_tokens=128)

    assert out == "A dog runs in a park."
    _, kwargs = fake_client.analyze.call_args
    assert kwargs["model_name"] == "pegasus1.5"
    assert kwargs["prompt"] == "What happens?"
    assert kwargs["max_tokens"] == 128


def test_analyze_video_missing_file(monkeypatch):
    monkeypatch.setenv("TWELVELABS_API_KEY", "k")
    with pytest.raises(FileNotFoundError):
        tla.analyze_video("/no/such/file.mp4")


def test_embed_text_returns_vector(monkeypatch):
    fake_seg = MagicMock(float_=[0.1] * 512)
    fake_client = MagicMock()
    fake_client.embed.create.return_value = MagicMock(
        text_embedding=MagicMock(segments=[fake_seg])
    )
    with patch.object(tla, "_make_client", return_value=fake_client):
        vec = tla.embed_text("a person walking a dog")
    assert len(vec) == 512
    _, kwargs = fake_client.embed.create.call_args
    assert kwargs["model_name"] == "marengo3.0"
    assert kwargs["text"] == "a person walking a dog"


# ===========================================================================
# Live test — only runs with a real key
# ===========================================================================
@pytest.mark.skipif(
    not os.environ.get("TWELVELABS_API_KEY"),
    reason="TWELVELABS_API_KEY not set",
)
def test_embed_text_live():
    pytest.importorskip("twelvelabs")
    vec = tla.embed_text("a person walking a dog")
    assert len(vec) == 512
    assert all(isinstance(x, float) for x in vec[:5])
