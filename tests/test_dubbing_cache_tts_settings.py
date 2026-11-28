import shutil
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg, params
from videotrans.configure.excepts import StopTask
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util.help_misc import vail_file

# (time, spoken text, translation) of each line
LINES = [
    ("00:00:00,500 --> 00:00:02,000", "谢谢你。", "Thank you."),
    ("00:00:02,500 --> 00:00:04,000", "明天见！", "See you tomorrow!"),
]

# the params keys of the settings that change the audio but aren't models, saved in
# each channel's settings window, which the channel reads when it dubs
SAVED_SETTINGS = {
    # instructions= (videotrans/tts/_openaitts.py)
    tts.OPENAI_TTS: ["openaitts_instructions"],
    # "emotion" of voice_setting (_minimaxi.py)
    tts.MINIMAXI_TTS: ["minimaxi_emotion"],
    # model.generate(cfg_weight=..., exaggeration=...) (_chatterbox.py)
    tts.CHATTERBOX_TTS: ["chatterbox_cfg_weight", "chatterbox_exaggeration"],
}

# each setting as its window saves it when it isn't changed
DEFAULTS = {
    "openaitts_instructions": "",
    "minimaxi_emotion": "happy",
    "chatterbox_cfg_weight": 0.5,
    "chatterbox_exaggeration": 0.5,
}

# (channel, setting, another value of it, a voice of the channel)
CHANGES = [
    pytest.param(
        tts.OPENAI_TTS,
        "openaitts_instructions",
        "Speak in a cheerful and positive tone.",
        "alloy",
        id="openai-instructions",
    ),
    pytest.param(
        tts.MINIMAXI_TTS,
        "minimaxi_emotion",
        "sad",
        "Graceful Lady",
        id="minimaxi-emotion",
    ),
    pytest.param(
        tts.CHATTERBOX_TTS,
        "chatterbox_cfg_weight",
        0.3,
        "default",
        id="chatterbox-cfg_weight",
    ),
    pytest.param(
        tts.CHATTERBOX_TTS,
        "chatterbox_exaggeration",
        0.8,
        "default",
        id="chatterbox-exaggeration",
    ),
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
    # the instructions are for gpt-4o-mini-tts
    monkeypatch.setattr(params, "openaitts_model", "gpt-4o-mini-tts")
    for key, value in DEFAULTS.items():
        monkeypatch.setattr(params, key, value)


def _settings(tts_type):
    # like the channels, the settings saved in params
    return ", ".join(str(params.get(key)) for key in SAVED_SETTINGS.get(tts_type, []))


def _audio(tts_type, voice):
    """The audio of a line dubbed with the settings saved now"""
    return f"{_settings(tts_type)}: {voice}".encode()


@pytest.fixture
def tts_calls(monkeypatch):
    """Stands in for the TTS channel and returns the settings and the lines it dubbed, per task"""
    calls = []

    def run_tts(*, queue_tts, tts_type, **kwargs):
        dubbed = []
        for it in queue_tts:
            # like the channels, a line whose wav is already there is skipped
            if vail_file(it["filename"]):
                continue
            # the audio depends on these settings as well as on the voice role
            Path(it["filename"]).write_bytes(_audio(tts_type, it["role"]))
            dubbed.append(it["line"])
        calls.append((_settings(tts_type), dubbed))

    monkeypatch.setattr(_stage_dubbing, "run_tts", run_tts)
    return calls


def _srt(times, texts):
    return "\n".join(
        f"{i}\n{t}\n{text}\n" for i, (t, text) in enumerate(zip(times, texts), 1)
    )


def _dub(tmp_path, tts_type, voice_role, clear_output=True):
    """Starts the video as the main window does; returns the audio of each line"""
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


@pytest.mark.parametrize("tts_type, key, value, voice", CHANGES)
def test_video_is_dubbed_again_after_changing_a_setting_in_the_channel_settings(
    monkeypatch, tmp_path, tts_calls, tts_type, key, value, voice
):
    first = _audio(tts_type, voice)
    assert _dub(tmp_path, tts_type, voice) == [first] * 2
    # change the setting in the channel's settings window and Start again
    monkeypatch.setattr(params, key, value)
    second = _audio(tts_type, voice)
    assert second != first
    assert _dub(tmp_path, tts_type, voice) == [second] * 2
    # going back to the first value takes its dubbing from the cache again
    monkeypatch.setattr(params, key, DEFAULTS[key])
    assert _dub(tmp_path, tts_type, voice) == [first] * 2
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], [1, 2], []]


def test_rerun_with_the_subtitles_of_the_run_before_uses_the_changed_setting(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "openaitts_instructions", "Speak calmly.")
    assert (
        _dub(tmp_path, tts.OPENAI_TTS, "alloy", clear_output=False)
        == [b"Speak calmly.: alloy"] * 2
    )
    # this run reads the target subtitles that dubbing() saved, in which line 1 has
    # lost its "." at the end and line 2 is unchanged
    monkeypatch.setattr(params, "openaitts_instructions", "Whisper.")
    assert (
        _dub(tmp_path, tts.OPENAI_TTS, "alloy", clear_output=False)
        == [b"Whisper.: alloy"] * 2
    )
    assert tts_calls == [("Speak calmly.", [1, 2]), ("Whisper.", [1, 2])]


def test_same_settings_still_use_the_cache(monkeypatch, tmp_path, tts_calls):
    monkeypatch.setattr(params, "minimaxi_emotion", "sad")
    sad = [b"sad: Graceful Lady"] * 2
    assert _dub(tmp_path, tts.MINIMAXI_TTS, "Graceful Lady") == sad
    assert _dub(tmp_path, tts.MINIMAXI_TTS, "Graceful Lady") == sad
    assert tts_calls == [("sad", [1, 2]), ("sad", [])]


def test_lines_cached_before_these_settings_were_in_the_key_are_dubbed_again(
    monkeypatch, tmp_path, tts_calls
):
    # lines cached under the key without these settings could hold audio made with any
    # value, so the key ends with the values even when they are empty
    style_params = getattr(_stage_dubbing, "TTS_STYLE_PARAMS", {})
    monkeypatch.setattr(params, "openaitts_instructions", "")
    monkeypatch.setattr(_stage_dubbing, "TTS_STYLE_PARAMS", {}, raising=False)
    assert _dub(tmp_path, tts.OPENAI_TTS, "alloy") == [b": alloy"] * 2
    monkeypatch.setattr(_stage_dubbing, "TTS_STYLE_PARAMS", style_params, raising=False)
    assert _dub(tmp_path, tts.OPENAI_TTS, "alloy") == [b": alloy"] * 2
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], [1, 2]]


def test_default_index_tts_task_keeps_the_cache_key_used_before_emotion_support(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "index_version", 1)
    monkeypatch.setattr(params, "index_emo_vector", "")
    monkeypatch.setattr(params, "index_emo_weight", 0.65)
    suffix = _stage_dubbing.emotion_cache_suffix
    monkeypatch.setattr(_stage_dubbing, "emotion_cache_suffix", lambda *_: "")
    expected = _dub(tmp_path, tts.INDEX_TTS, "clone")
    monkeypatch.setattr(_stage_dubbing, "emotion_cache_suffix", suffix)
    assert _dub(tmp_path, tts.INDEX_TTS, "clone") == expected
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], []]


def test_index_emotion_request_changes_its_cache_key(monkeypatch, tmp_path, tts_calls):
    monkeypatch.setattr(params, "index_version", 0)
    monkeypatch.setattr(params, "index_emo_vector", "0.8,0,0,0,0,0,0,0")
    monkeypatch.setattr(params, "index_emo_weight", 0.4)
    expected = _dub(tmp_path, tts.INDEX_TTS, "clone")

    monkeypatch.setattr(params, "index_version", 1)
    monkeypatch.setattr(params, "index_emo_vector", "")
    # V2 is another model: these lines are dubbed again (the last assert)
    assert _dub(tmp_path, tts.INDEX_TTS, "clone") == expected

    monkeypatch.setattr(params, "index_emo_vector", "0.8,0,0,0,0,0,0,0")
    assert _dub(tmp_path, tts.INDEX_TTS, "clone") == expected

    monkeypatch.setattr(params, "index_emo_weight", 0.5)
    assert _dub(tmp_path, tts.INDEX_TTS, "clone") == expected
    assert [dubbed for _, dubbed in tts_calls] == [
        [1, 2],
        [1, 2],
        [1, 2],
        [1, 2],
    ]


@pytest.mark.parametrize(
    "first_version, second_version",
    [
        pytest.param(1, 2, id="v2-to-v2.5"),
        pytest.param(2, 0, id="v2.5-to-v1"),
    ],
)
def test_switching_index_version_dubs_the_same_video_again(
    monkeypatch, tmp_path, tts_calls, first_version, second_version
):
    monkeypatch.setattr(params, "index_version", first_version)
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    monkeypatch.setattr(params, "index_version", second_version)
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], [1, 2]]


def test_same_index_version_uses_the_shared_cache(monkeypatch, tmp_path, tts_calls):
    monkeypatch.setattr(params, "index_version", "2")
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    monkeypatch.setattr(params, "index_version", 2)
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], []]


def test_default_v2_keeps_the_key_without_a_version_suffix(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "index_version", 1)
    suffix = _stage_dubbing.version_cache_suffix
    monkeypatch.setattr(_stage_dubbing, "version_cache_suffix", lambda *_: "")
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    monkeypatch.setattr(_stage_dubbing, "version_cache_suffix", suffix)
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], []]


def test_bad_index_version_stops_before_any_line_is_dubbed(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "index_version", "abc")
    with pytest.raises(StopTask, match="invalid literal"):
        _dub(tmp_path, tts.INDEX_TTS, "clone")
    assert tts_calls == []


def test_other_video_channels_ignore_index_version(monkeypatch, tmp_path, tts_calls):
    monkeypatch.setattr(params, "index_version", 1)
    _dub(tmp_path, tts.OPENAI_TTS, "alloy")
    monkeypatch.setattr(params, "index_version", 2)
    _dub(tmp_path, tts.OPENAI_TTS, "alloy")
    assert [dubbed for _, dubbed in tts_calls] == [[1, 2], []]


def test_bad_index_emotion_stops_while_building_the_cache_key(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "index_version", 1)
    monkeypatch.setattr(params, "index_emo_vector", "")
    _dub(tmp_path, tts.INDEX_TTS, "clone")
    tts_calls.clear()
    monkeypatch.setattr(params, "index_emo_vector", "0.8,0")
    with pytest.raises(StopTask, match="exactly 8"):
        _dub(tmp_path, tts.INDEX_TTS, "clone")
    assert tts_calls == []


def test_these_settings_change_the_keys_of_their_own_channel_only(
    monkeypatch, tmp_path, tts_calls
):
    def keys(tts_type, values, name):
        for key, value in values.items():
            monkeypatch.setattr(params, key, value)
        cache = tmp_path / f"cache-{tts_type}-{name}"
        cache.mkdir()
        monkeypatch.setattr(_stage_dubbing, "DUBBING_CACHE", cache.as_posix())
        _dub(tmp_path, tts_type, "voice-1")
        return sorted(it.name for it in cache.iterdir())

    others = {
        "openaitts_instructions": "Whisper.",
        "minimaxi_emotion": "sad",
        "chatterbox_cfg_weight": 0.3,
        "chatterbox_exaggeration": 0.8,
    }
    changed = []
    for tts_type in tts.ID_NAME_DICT:
        before = keys(tts_type, DEFAULTS, "before")
        after = keys(tts_type, others, "after")
        assert len(before) == len(after) == 2
        if before != after:
            changed.append(tts_type)
    assert sorted(changed) == sorted(SAVED_SETTINGS)
