import shutil
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg, params
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util.help_misc import vail_file

# (time, spoken text, translation) of each line
LINES = [
    ("00:00:00,500 --> 00:00:02,000", "谢谢你。", "Thank you."),
    ("00:00:02,500 --> 00:00:04,000", "明天见！", "See you tomorrow!"),
]

# the params key of the model chosen in each channel's settings window, which the channel
# reads when it dubs (videotrans/tts/_openaitts.py, _elevenlabs.py, ...); Audio.cpp reads
# it only when the task passes no model (_audiocpp.py)
SAVED_MODEL = {
    tts.OPENAI_TTS: "openaitts_model",
    tts.ELEVENLABS_TTS: "elevenlabstts_model",
    tts.MINIMAXI_TTS: "minimaxi_tts_model",
    tts.GEMINI_TTS: "gemini_ttsmodel",
    tts.OPENROUTER_API: "openrouter_tts_model",
    tts.SILICONFLOW_API: "siliconflow_tts_model",
    tts.BAILIAN_TTS: "bailian_ttsmodel",
    tts.XIAOMI_TTS: "xiaomi_ttsmodel",
    tts.FISHAUDIOAPI_TTS: "fishaudio_model",
    tts.AUDIOCPP_TTS: "audiocpp_model",
}

# (channel, two models of its settings window, a voice that both models have)
CHANNELS = [
    pytest.param(tts.OPENAI_TTS, "tts-1", "gpt-4o-mini-tts", "alloy", id="openai"),
    pytest.param(
        tts.ELEVENLABS_TTS,
        "eleven_multilingual_v2",
        "eleven_v3",
        "Sarah - Mature Reassuring Confident",
        id="elevenlabs",
    ),
    pytest.param(
        tts.MINIMAXI_TTS,
        "speech-02-hd",
        "speech-2.8-hd",
        "Graceful Lady",
        id="minimaxi",
    ),
    pytest.param(
        tts.GEMINI_TTS,
        "gemini-2.5-flash-preview-tts",
        "gemini-2.5-pro-preview-tts",
        "Kore",
        id="gemini",
    ),
    # the voice lists of both OpenRouter models have leo
    pytest.param(
        tts.OPENROUTER_API,
        "x-ai/grok-voice-tts-1.0",
        "canopylabs/orpheus-3b-0.1-ft",
        "leo",
        id="openrouter",
    ),
    pytest.param(
        tts.SILICONFLOW_API,
        "FunAudioLLM/CosyVoice2-0.5B",
        "fnlp/MOSS-TTSD-v0.5",
        "alex",
        id="siliconflow",
    ),
    pytest.param(
        tts.BAILIAN_TTS,
        "qwen3-tts-flash",
        "qwen3-tts-instruct-flash",
        "芊悦(Cherry)",
        id="bailian",
    ),
    # the XiaoMi window lists only mimo-v2.5-tts now, but it listed mimo-v2-tts too before,
    # and a model saved then stays in params until the window is saved again
    pytest.param(tts.XIAOMI_TTS, "mimo-v2-tts", "mimo-v2.5-tts", "Mia", id="xiaomi"),
    pytest.param(tts.FISHAUDIOAPI_TTS, "s2-pro", "s2.1-pro", "Sarah", id="fishaudio"),
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
def tts_calls(monkeypatch):
    """Stands in for the TTS channel and returns the model and the lines it dubbed, per task"""
    calls = []

    def run_tts(*, queue_tts, tts_type, model_name=None, **kwargs):
        # like the channels, the model saved in params, unless Audio.cpp is passed one
        if tts_type in SAVED_MODEL and not (
            tts_type == tts.AUDIOCPP_TTS and model_name
        ):
            model_name = params.get(SAVED_MODEL[tts_type])
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


def _dub(tmp_path, tts_type, voice_role, tts_model_name=None, clear_output=True):
    """Starts the video, as the main window does (it passes a model for Audio.cpp only);
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


@pytest.mark.parametrize("tts_type, first, second, voice", CHANNELS)
def test_video_is_dubbed_again_after_choosing_another_model_in_the_channel_settings(
    monkeypatch, tmp_path, tts_calls, tts_type, first, second, voice
):
    audio = {model: [f"{model}: {voice}".encode()] * 2 for model in (first, second)}
    monkeypatch.setattr(params, SAVED_MODEL[tts_type], first)
    assert _dub(tmp_path, tts_type, voice) == audio[first]
    # choose another model in the channel's settings window and Start again
    monkeypatch.setattr(params, SAVED_MODEL[tts_type], second)
    assert _dub(tmp_path, tts_type, voice) == audio[second]
    # going back to the first model takes its dubbing from the cache again
    monkeypatch.setattr(params, SAVED_MODEL[tts_type], first)
    assert _dub(tmp_path, tts_type, voice) == audio[first]
    assert tts_calls == [(first, [1, 2]), (second, [1, 2]), (first, [])]


def test_rerun_with_the_subtitles_of_the_run_before_uses_another_saved_model(
    monkeypatch, tmp_path, tts_calls
):
    monkeypatch.setattr(params, "openaitts_model", "tts-1")
    assert (
        _dub(tmp_path, tts.OPENAI_TTS, "alloy", clear_output=False)
        == [b"tts-1: alloy"] * 2
    )
    # this run reads the target subtitles that dubbing() saved, in which line 1 has
    # lost its "." at the end and line 2 is unchanged
    monkeypatch.setattr(params, "openaitts_model", "gpt-4o-mini-tts")
    assert (
        _dub(tmp_path, tts.OPENAI_TTS, "alloy", clear_output=False)
        == [b"gpt-4o-mini-tts: alloy"] * 2
    )
    assert tts_calls == [("tts-1", [1, 2]), ("gpt-4o-mini-tts", [1, 2])]


def test_same_saved_model_still_uses_the_cache(monkeypatch, tmp_path, tts_calls):
    monkeypatch.setattr(params, "openaitts_model", "tts-1")
    assert _dub(tmp_path, tts.OPENAI_TTS, "alloy") == [b"tts-1: alloy"] * 2
    assert _dub(tmp_path, tts.OPENAI_TTS, "alloy") == [b"tts-1: alloy"] * 2
    assert tts_calls == [("tts-1", [1, 2]), ("tts-1", [])]


def test_audiocpp_task_without_a_model_uses_the_saved_model(
    monkeypatch, tmp_path, tts_calls
):
    omnivoice = [b"omnivoice: en_female_1.wav"] * 2
    qwen3_tts = [b"qwen3_tts: en_female_1.wav"] * 2
    # cli.py without --tts_model_name passes no model to the task
    monkeypatch.setattr(params, "audiocpp_model", "omnivoice")
    assert _dub(tmp_path, tts.AUDIOCPP_TTS, "en_female_1.wav") == omnivoice
    # another model saved by Start in the main window or a dubbing window
    monkeypatch.setattr(params, "audiocpp_model", "qwen3_tts")
    assert _dub(tmp_path, tts.AUDIOCPP_TTS, "en_female_1.wav") == qwen3_tts
    # the main window passes the same model, and its lines come from the cache
    assert _dub(tmp_path, tts.AUDIOCPP_TTS, "en_female_1.wav", "qwen3_tts") == qwen3_tts
    assert tts_calls == [
        ("omnivoice", [1, 2]),
        ("qwen3_tts", [1, 2]),
        ("qwen3_tts", []),
    ]


def test_task_model_does_not_replace_the_saved_model_of_other_channels(
    monkeypatch, tmp_path, tts_calls
):
    # cli.py --tts_model_name passes a model to the task, which only Audio.cpp uses
    monkeypatch.setattr(params, "openaitts_model", "tts-1")
    assert _dub(tmp_path, tts.OPENAI_TTS, "alloy", "foo") == [b"tts-1: alloy"] * 2
    monkeypatch.setattr(params, "openaitts_model", "gpt-4o-mini-tts")
    assert (
        _dub(tmp_path, tts.OPENAI_TTS, "alloy", "foo")
        == [b"gpt-4o-mini-tts: alloy"] * 2
    )
    assert tts_calls == [("tts-1", [1, 2]), ("gpt-4o-mini-tts", [1, 2])]
