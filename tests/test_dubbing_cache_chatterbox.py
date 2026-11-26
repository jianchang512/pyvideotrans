import shutil
import sys
import types
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate

# (time, spoken text, translation) of each line
LINES = [
    ("00:00:00,500 --> 00:00:02,000", "谢谢你。", "Thank you."),
    ("00:00:02,500 --> 00:00:04,000", "明天见！", "See you tomorrow!"),
]


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    # every line is dubbed with voice_role
    monkeypatch.setattr(app_cfg, "line_roles", {})
    # the cache that _tts() shares between tasks
    cache = tmp_path / "dubbing_cache"
    cache.mkdir()
    monkeypatch.setattr(_stage_dubbing, "DUBBING_CACHE", cache.as_posix())


@pytest.fixture
def model(monkeypatch):
    """Stands in for the ChatterBox model, its download, torch, soundfile and ffmpeg;
    returns the texts the model dubbed and the texts it fails on"""
    model = types.SimpleNamespace(dubbed=[], fails_on=set())

    class Audio:
        """The tensor that the model generates, here the text of the line"""

        ndim = 1

        def __init__(self, text):
            self.text = text

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.text

    class Model:
        sr = 24000

        def generate(self, text, **kwargs):
            if text in model.fails_on:
                raise RuntimeError(f"CUDA out of memory: {text}")
            model.dubbed.append(text)
            return Audio(text)

    mtl_tts = types.ModuleType("chatterbox.mtl_tts")
    mtl_tts.ChatterboxMultilingualTTS = types.SimpleNamespace(
        from_local=lambda local_dir, **kwargs: Model()
    )
    monkeypatch.setitem(sys.modules, "chatterbox", types.ModuleType("chatterbox"))
    monkeypatch.setitem(sys.modules, "chatterbox.mtl_tts", mtl_tts)
    # the device helpers of videotrans.util.gpus import torch; the model runs on the CPU
    gpus = types.ModuleType("videotrans.util.gpus")
    gpus.mps_or_cpu = gpus.resolve_torch_device = lambda *args, **kwargs: "cpu"
    monkeypatch.setitem(sys.modules, "videotrans.util.gpus", gpus)
    from videotrans.tts import _chatterbox

    # the model is already downloaded
    monkeypatch.setattr(_chatterbox.ChatterBoxTTS, "_download", lambda self: True)
    # soundfile saves the audio of the model as <line>.wav-24k.wav
    monkeypatch.setattr(
        _chatterbox,
        "sf",
        types.SimpleNamespace(
            write=lambda file, data, samplerate, **kwargs: Path(file).write_text(
                data, encoding="utf-8"
            )
        ),
    )
    # instead of ffmpeg, which converts it to the 48 kHz stereo wav of the line
    monkeypatch.setattr(
        _chatterbox.ChatterBoxTTS,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copy(src, dst)),
    )
    return model


def _srt(times, texts):
    return "\n".join(
        f"{i}\n{t}\n{text}\n" for i, (t, text) in enumerate(zip(times, texts), 1)
    )


def _dub(tmp_path):
    """Starts the video with ChatterBox as the main window does; returns the audio
    of each line, None for a line without audio"""
    trk = TransCreate(
        cfg=TaskCfgVTT(
            name=(tmp_path / "video.mp4").as_posix(),
            noextname="video",
            uuid="video-uuid",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "tmp").as_posix(),
            source_language_code="zh-cn",
            target_language_code="en",
            voice_role="default",
            tts_type=tts.CHATTERBOX_TTS,
            # "Clear Output", checked by default, deletes the subtitles of the run before
            clear_cache=True,
        )
    )
    Path(trk.cfg.target_dir).mkdir(parents=True, exist_ok=True)
    Path(trk.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
    # recogn() and trans() make the subtitles
    times = [it[0] for it in LINES]
    source = _srt(times, [it[1] for it in LINES])
    Path(trk.cfg.source_sub).write_text(source, encoding="utf-8")
    target = _srt(times, [it[2] for it in LINES])
    Path(trk.cfg.target_sub).write_text(target, encoding="utf-8")
    try:
        trk.dubbing()
        return [
            Path(it["filename"]).read_bytes() if Path(it["filename"]).exists() else None
            for it in trk.queue_tts
        ]
    finally:
        # a finished task deletes its folder
        shutil.rmtree(trk.cfg.cache_folder)


def test_start_again_with_the_same_settings_uses_the_cached_dubbing(tmp_path, model):
    audio = [b"Thank you.", b"See you tomorrow!"]
    assert _dub(tmp_path) == audio
    # Start again: both lines come from the cache
    assert _dub(tmp_path) == audio
    assert model.dubbed == ["Thank you.", "See you tomorrow!"]


def test_line_that_fails_again_is_left_without_audio_as_in_the_first_run(
    tmp_path, model
):
    model.fails_on = {"See you tomorrow!"}
    # like a line that fails next to a line dubbed in the same run
    assert _dub(tmp_path) == [b"Thank you.", None]
    # Start again: line 1 comes from the cache and line 2 fails again
    assert _dub(tmp_path) == [b"Thank you.", None]
    assert model.dubbed == ["Thank you."]


def test_task_fails_with_the_error_of_the_model_when_no_line_is_dubbed(tmp_path, model):
    model.fails_on = {"Thank you.", "See you tomorrow!"}
    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        _dub(tmp_path)
    assert model.dubbed == []
