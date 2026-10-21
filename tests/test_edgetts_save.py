import asyncio
from pathlib import Path

import pytest

edge_tts = pytest.importorskip("edge_tts")

from videotrans.tts import _edgetts
from videotrans.tts._edgetts import _save_atomic


class _FakeCommunicate:
    def __init__(self, data=b"", exc=None, hang=False):
        self.data, self.exc, self.hang = data, exc, hang

    async def save(self, path):
        Path(path).write_bytes(self.data)
        if self.hang:
            await asyncio.sleep(10)
        if self.exc:
            raise self.exc


def test_success_writes_final_file(tmp_path):
    mp3 = str(tmp_path / "a.wav.mp3")
    asyncio.run(_save_atomic(_FakeCommunicate(b"audio"), mp3))
    assert Path(mp3).read_bytes() == b"audio"
    assert not Path(mp3 + ".part").exists()


def test_dropped_connection_leaves_no_partial_file(tmp_path):
    mp3 = str(tmp_path / "a.wav.mp3")
    err = edge_tts.exceptions.WebSocketError("dropped")
    with pytest.raises(edge_tts.exceptions.EdgeTTSException):
        asyncio.run(_save_atomic(_FakeCommunicate(b"half", exc=err), mp3))
    assert not Path(mp3).exists()
    assert not Path(mp3 + ".part").exists()


def test_timeout_leaves_no_partial_file(tmp_path, monkeypatch):
    monkeypatch.setattr(_edgetts, "SAVE_TIMEOUT", 0.05)
    mp3 = str(tmp_path / "a.wav.mp3")
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(_save_atomic(_FakeCommunicate(b"half", hang=True), mp3))
    assert not Path(mp3).exists()
    assert not Path(mp3 + ".part").exists()


def test_empty_audio_is_an_error(tmp_path):
    mp3 = str(tmp_path / "a.wav.mp3")
    with pytest.raises(edge_tts.exceptions.EdgeTTSException):
        asyncio.run(_save_atomic(_FakeCommunicate(b""), mp3))
    assert not Path(mp3).exists()
