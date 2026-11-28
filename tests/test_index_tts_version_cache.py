import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg, params
from videotrans.configure.excepts import StopTask
from videotrans.task import dubbing
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import SrtItem, TaskCfgTTS
from videotrans.tts import _index_emotion


@pytest.mark.parametrize(
    "values, expected",
    [
        ({}, ""),
        ({"index_version": "1"}, ""),
        ({"index_version": "2"}, "-v2"),
        ({"index_version": 2}, "-v2"),
        ({"index_version": 0}, "-v0"),
        ({"index_version": 3}, "-v3"),
    ],
)
def test_version_cache_suffix(values, expected):
    assert _index_emotion.version_cache_suffix(values) == expected


def test_version_cache_suffix_rejects_bad_saved_value():
    with pytest.raises(ValueError):
        _index_emotion.version_cache_suffix({"index_version": "abc"})


def _subtitle_task_filename(monkeypatch, tmp_path, tts_type, version, run_tts=None):
    monkeypatch.setitem(params, "index_version", version)
    monkeypatch.setitem(params, "index_emo_vector", "")
    monkeypatch.setitem(params, "index_role_emotions", "")
    monkeypatch.setattr(app_cfg, "dubbing_role", {})
    queued = []
    if run_tts is None:
        run_tts = lambda **kwargs: queued.extend(kwargs["queue_tts"])
    monkeypatch.setattr(tts, "run", run_tts)
    source = tmp_path / "input.srt"
    source.write_text("", encoding="utf-8")
    task = DubbingSrt(
        cfg=TaskCfgTTS(
            name=source.as_posix(),
            noextname=source.stem,
            uuid="subtitle-uuid",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "subtitle-cache").as_posix(),
            target_language_code="en",
            voice_role="man.wav",
            tts_type=tts_type,
        ),
        subs=[
            SrtItem(
                line=1,
                start_time=500,
                end_time=2000,
                startraw="00:00:00,500",
                endraw="00:00:02,000",
                text="Hello there.",
            )
        ],
    )
    task._tts()
    return queued[0]["filename"]


def test_subtitle_task_filenames_separate_versions_and_keep_v2_base(
    monkeypatch, tmp_path
):
    v25 = _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, 2)
    v1 = _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, 0)
    assert v25 != v1

    suffix = dubbing.version_cache_suffix
    monkeypatch.setattr(dubbing, "version_cache_suffix", lambda *_: "")
    base = _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, 1)
    monkeypatch.setattr(dubbing, "version_cache_suffix", suffix)
    v2 = _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, 1)
    assert v2 == base


def test_subtitle_task_bad_version_stops_before_tts(monkeypatch, tmp_path):
    with pytest.raises(StopTask, match="invalid literal"):
        _subtitle_task_filename(
            monkeypatch,
            tmp_path,
            tts.INDEX_TTS,
            "abc",
            lambda **kwargs: pytest.fail("TTS was called"),
        )


def test_subtitle_task_other_channels_ignore_index_version(monkeypatch, tmp_path):
    first = _subtitle_task_filename(monkeypatch, tmp_path, tts.OPENAI_TTS, 1)
    second = _subtitle_task_filename(monkeypatch, tmp_path, tts.OPENAI_TTS, 2)
    assert first == second
