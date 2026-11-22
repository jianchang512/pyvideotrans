import shutil
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util.help_misc import vail_file

# (time, spoken text, translation) of each line
LINES = [
    ("00:00:00,500 --> 00:00:02,000", "谢谢你。", "Thank you."),
    ("00:00:02,500 --> 00:00:04,000", "明天见！", "See you tomorrow!"),
]
OMNIVOICE = b"omnivoice: en_female_1.wav"
QWEN3_TTS = b"qwen3_tts: en_female_1.wav"


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
def tts_calls(monkeypatch):
    """Stands in for the TTS channel and returns the model and the lines it dubbed, per task"""
    calls = []

    def run_tts(*, queue_tts, model_name=None, **kwargs):
        dubbed = []
        for it in queue_tts:
            # like the channels, a line whose wav is already there is skipped
            if vail_file(it["filename"]):
                continue
            # the voice depends on the model as well as on the voice role
            Path(it["filename"]).write_bytes(f"{model_name}: {it['role']}".encode())
            dubbed.append(it["line"])
        calls.append((model_name, dubbed))

    monkeypatch.setattr(_stage_dubbing, "run_tts", run_tts)
    return calls


def _srt(times, texts):
    return "\n".join(
        f"{i}\n{t}\n{text}\n" for i, (t, text) in enumerate(zip(times, texts), 1)
    )


def _dub(
    tmp_path,
    tts_model_name,
    tts_type=tts.AUDIOCPP_TTS,
    voice_role="en_female_1.wav",
    clear_output=True,
):
    """Starts the video, as the main window does with the model chosen next to the channel;
    returns the audio of each line"""
    trk = TransCreate(
        cfg=TaskCfgVTT(
            name=(tmp_path / "video.mp4").as_posix(),
            noextname="video",
            uuid="video-uuid",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "tmp").as_posix(),
            source_language_code="zh-cn",
            target_language_code="en",
            voice_role=voice_role,
            tts_type=tts_type,
            tts_model_name=tts_model_name,
            # "Clear Output", checked by default, deletes the subtitles of the run before
            clear_cache=clear_output,
        )
    )
    Path(trk.cfg.target_dir).mkdir(parents=True, exist_ok=True)
    Path(trk.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
    times = [it[0] for it in LINES]
    # recogn() and trans() make the subtitles when they aren't there
    if not Path(trk.cfg.source_sub).exists():
        source = _srt(times, [it[1] for it in LINES])
        Path(trk.cfg.source_sub).write_text(source, encoding="utf-8")
    if not Path(trk.cfg.target_sub).exists():
        target = _srt(times, [it[2] for it in LINES])
        Path(trk.cfg.target_sub).write_text(target, encoding="utf-8")
    trk.dubbing()
    audio = [Path(it["filename"]).read_bytes() for it in trk.queue_tts]
    # a finished task deletes its folder
    shutil.rmtree(trk.cfg.cache_folder)
    return audio


def test_video_is_dubbed_again_with_another_audiocpp_model(tmp_path, tts_calls):
    assert _dub(tmp_path, "omnivoice") == [OMNIVOICE, OMNIVOICE]
    # Start again after choosing another model
    assert _dub(tmp_path, "qwen3_tts") == [QWEN3_TTS, QWEN3_TTS]
    # going back to the first model takes its dubbing from the cache again
    assert _dub(tmp_path, "omnivoice") == [OMNIVOICE, OMNIVOICE]
    assert tts_calls == [
        ("omnivoice", [1, 2]),
        ("qwen3_tts", [1, 2]),
        ("omnivoice", []),
    ]


def test_rerun_with_the_subtitles_of_the_run_before_uses_another_audiocpp_model(
    tmp_path, tts_calls
):
    assert _dub(tmp_path, "omnivoice", clear_output=False) == [OMNIVOICE, OMNIVOICE]
    # this run reads the target subtitles that dubbing() saved, in which line 1 has
    # lost its "." at the end and line 2 is unchanged
    assert _dub(tmp_path, "qwen3_tts", clear_output=False) == [QWEN3_TTS, QWEN3_TTS]
    assert tts_calls == [("omnivoice", [1, 2]), ("qwen3_tts", [1, 2])]


def test_same_audiocpp_model_still_uses_the_cache(tmp_path, tts_calls):
    assert _dub(tmp_path, "omnivoice") == [OMNIVOICE, OMNIVOICE]
    assert _dub(tmp_path, "omnivoice") == [OMNIVOICE, OMNIVOICE]
    assert tts_calls == [("omnivoice", [1, 2]), ("omnivoice", [])]


def test_channel_without_a_model_choice_still_uses_the_cache(tmp_path, tts_calls):
    voice = "en-US-AriaNeural"
    audio = f"None: {voice}".encode()
    assert _dub(tmp_path, None, tts.EDGE_TTS, voice) == [audio, audio]
    assert _dub(tmp_path, None, tts.EDGE_TTS, voice) == [audio, audio]
    assert tts_calls == [(None, [1, 2]), (None, [])]
