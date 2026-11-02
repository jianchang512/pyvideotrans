import json
import shutil
import sys
import types
from pathlib import Path

import pytest

# the worker saves the audio from the model with soundfile
pytest.importorskip("soundfile")

import numpy as np
import soundfile as sf

from videotrans.process import qwen_tts
from videotrans.util.help_misc import vail_file

# a re-dubbed line is converted with ffmpeg
needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)

# 1 s of a 440 Hz tone at 24 kHz, the audio of every line
AUDIO = (0.3 * np.sin(2 * np.pi * 440 * np.arange(24000) / 24000)).astype(np.float32)


@pytest.fixture
def calls(monkeypatch):
    """Stands in for torch and the Qwen3-TTS models; returns the voice of each
    line the models generated"""
    calls = []

    class Model:
        device = "cpu"

        # a preset voice, such as Vivian, of the CustomVoice model
        def generate_custom_voice(self, **kwargs):
            calls.append(kwargs["speaker"])
            return [AUDIO], 24000

        # clone or a reference audio, with the Base model
        def generate_voice_clone(self, **kwargs):
            calls.append("clone")
            return [AUDIO], 24000

    qwen = types.ModuleType("qwen_tts")
    qwen.Qwen3TTSModel = types.SimpleNamespace(
        from_pretrained=lambda path, **kwargs: Model()
    )
    monkeypatch.setitem(sys.modules, "qwen_tts", qwen)
    monkeypatch.setitem(sys.modules, "torch", types.ModuleType("torch"))
    return calls


def _lines(tmp_path, roles):
    ref_wav = (tmp_path / "ref.wav").as_posix()
    sf.write(ref_wav, AUDIO, 24000)
    return [
        {
            "line": i + 1,
            "text": f"line {i + 1}",
            "role": role,
            "filename": (tmp_path / f"{i}.wav").as_posix(),
            "ref_wav": ref_wav if role == "clone" else "",
            "ref_text": "",
        }
        for i, role in enumerate(roles)
    ]


def _redub(monkeypatch, tmp_path, lines):
    """Re-dubs the lines like the proofreading panel: the worker takes them from
    the re-dub queue in each pass, until the panel is closed after 3 passes"""
    queue = tmp_path / "redubbing.json"
    stop = tmp_path / "stopredubbing.pid"
    queue.write_text(json.dumps(lines), encoding="utf-8")
    monkeypatch.setattr(qwen_tts, "REDUBB_QUEUE_FILE", queue.as_posix())
    monkeypatch.setattr(qwen_tts, "REDUBB_STATUS_FILE", stop.as_posix())
    passes = []

    # the worker waits 1 s after each pass; closing the panel writes the stop file
    def sleep(seconds):
        passes.append(seconds)
        if len(passes) == 3:
            stop.write_text("end")

    monkeypatch.setattr(qwen_tts, "time", types.SimpleNamespace(sleep=sleep))
    assert qwen_tts.qwen3tts_fun(language="English", is_redubb=True) == (True, None)
    assert len(passes) == 3


@needs_ffmpeg
@pytest.mark.parametrize("role", ["Vivian", "clone"])
def test_redubbed_line_is_saved(monkeypatch, tmp_path, calls, role):
    lines = _lines(tmp_path, [role])
    _redub(monkeypatch, tmp_path, lines)
    # generated in the first pass and saved as the line's 48 kHz stereo wav,
    # which the panel waits for, so the next passes skip the line
    assert calls == [role]
    info = sf.info(lines[0]["filename"])
    assert (info.samplerate, info.channels) == (48000, 2)


@needs_ffmpeg
def test_preset_voice_line_is_converted_like_a_clone_line(monkeypatch, tmp_path, calls):
    lines = _lines(tmp_path, ["Vivian", "clone"])
    _redub(monkeypatch, tmp_path, lines)
    assert calls == ["Vivian", "clone"]
    # the model gave both lines the same audio
    preset, clone = (Path(it["filename"]) for it in lines)
    assert vail_file(preset.as_posix())
    assert preset.read_bytes() == clone.read_bytes()


def test_first_dubbing_leaves_the_conversion_to_the_main_process(tmp_path, calls):
    lines = _lines(tmp_path, ["Vivian", "clone"])
    queue = tmp_path / "queuetts.json"
    queue.write_text(json.dumps(lines), encoding="utf-8")
    assert qwen_tts.qwen3tts_fun(
        queue_tts_file=queue.as_posix(), language="English"
    ) == (True, None)
    assert calls == ["Vivian", "clone"]
    # QwenttsLocal._exec() converts each -24k.wav in the main process afterwards
    for it in lines:
        assert vail_file(it["filename"] + "-24k.wav")
        assert not Path(it["filename"]).exists()
