from unittest.mock import Mock

import pytest

from videotrans.recognition import _qwenasrlocal as qwen


@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setattr(qwen, "ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(qwen.BaseRecogn, "__post_init__", lambda self: None)
    return qwen.QwenasrlocalRecogn


def test_custom_snapshot_is_read_only(backend, tmp_path, monkeypatch):
    snapshot = tmp_path / "custom-model"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}")
    engine = backend(model_name=str(snapshot))
    assert engine.local_dir == str(snapshot)
    download = Mock()
    monkeypatch.setattr(qwen, "is_connect_hf", lambda: True)
    monkeypatch.setattr(qwen, "check_and_down_hf", download)
    engine._download()
    assert download.call_count == 1
    assert download.call_args.kwargs["repo_id"] == "Qwen/Qwen3-ForcedAligner-0.6B-hf"
    assert download.call_args.kwargs["local_dir"] == engine.aligner_dir


@pytest.mark.parametrize("name, size", [("1.7B", "1.7B"), ("0.6B", "0.6B"), ("tiny", "0.6B")])
def test_stock_model_and_legacy_fallback(backend, name, size):
    engine = backend(model_name=name)
    assert engine.asr_repo == f"Qwen/Qwen3-ASR-{size}-hf"


def test_missing_local_checkpoint_does_not_silently_select_stock_model(backend, tmp_path):
    with pytest.raises(ValueError, match="Missing config.json"):
        backend(model_name=str(tmp_path / "missing"))
