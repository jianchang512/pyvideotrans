import shutil
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, params
from videotrans.configure.excepts import StopTask
from videotrans.task import _stage_dubbing, dubbing
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import SrtItem, TaskCfgTTS, TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.tts import _index
from videotrans.tts._gradio import GradioBase
from videotrans.tts._index_emotion import (
    emotion_cache_suffix,
    index_emotion_for_role,
    parse_role_emotions,
)

VECTOR = "0.8,0,0,0,0,0,0,0"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("man.wav = 0.8,0,0,0,0,0,0,0", ([0.8] + [0.0] * 7, 0.65)),
        ("man.wav = 0.8,0,0,0,0,0,0,0 ; 0.7", ([0.8] + [0.0] * 7, 0.7)),
        ("man.wav＝0.8，0、0，0、0，0、0，0；0.4", ([0.8] + [0.0] * 7, 0.4)),
    ],
)
def test_parse_role_emotions_accepts_supported_formats(text, expected):
    assert parse_role_emotions(text) == {"man.wav": expected}


def test_role_without_weight_uses_global_weight_and_explicit_weight_wins():
    text = f"man.wav = {VECTOR}\nwoman.wav = {VECTOR} ; 0.7"
    assert parse_role_emotions(text, 0.2) == {
        "man.wav": ([0.8] + [0.0] * 7, 0.2),
        "woman.wav": ([0.8] + [0.0] * 7, 0.7),
    }


def test_full_width_semicolon_is_preserved_in_role_name():
    assert parse_role_emotions(f"x；y.wav = {VECTOR}") == {
        "x；y.wav": ([0.8] + [0.0] * 7, 0.65)
    }


def test_parse_role_emotions_ignores_comments_and_blank_lines_and_zero_disables():
    text = f"\n# role settings\n man.wav = {VECTOR}\n\nwoman.wav = 0,0,0,0,0,0,0,0\n"
    assert parse_role_emotions(text) == {
        "man.wav": ([0.8] + [0.0] * 7, 0.65),
        "woman.wav": None,
    }


@pytest.mark.parametrize(
    "text, line_number, message",
    [
        (f"man.wav = {VECTOR}\nman.wav = {VECTOR}", 2, "duplicates"),
        ("# ignored\nwoman.wav = 0.8,0", 2, "exactly 8"),
        (f"\nwoman.wav = {VECTOR} ; heavy", 2, "weight must be a number"),
        (f"woman.wav = {VECTOR} ; 1.5", 1, "between 0 and 1"),
        (f"woman.wav = {VECTOR} ;", 1, "weight must be a number"),
        ("\nwoman.wav 0.8,0,0,0,0,0,0,0", 2, "contain '='"),
        (f" = {VECTOR}", 1, "role name"),
        (f"a=b.wav = {VECTOR}", 1, "only numbers"),
        (f"woman.wav = {VECTOR} ; 0.2 ; 0.3", 1, "too many weights"),
    ],
)
def test_parse_role_emotions_reports_bad_line(text, line_number, message):
    with pytest.raises(ValueError, match=rf"line {line_number}.*{message}"):
        parse_role_emotions(text)


def test_role_lookup_precedence_global_fallback_and_none():
    values = {
        "index_version": 1,
        "index_emo_vector": "0,0.6,0,0,0,0,0,0",
        "index_emo_weight": 0.3,
        "index_role_emotions": f"man.wav = {VECTOR}",
    }
    assert index_emotion_for_role(values, "man.wav") == ([0.8] + [0.0] * 7, 0.3)
    values["index_role_emotions"] = f"man.wav = {VECTOR} ; 0.7"
    assert index_emotion_for_role(values, "man.wav") == ([0.8] + [0.0] * 7, 0.7)
    assert index_emotion_for_role(values, "woman.wav") == (
        [0.0, 0.6] + [0.0] * 6,
        0.3,
    )
    values["index_emo_vector"] = ""
    assert index_emotion_for_role(values, "woman.wav") is None


def test_zero_role_override_suppresses_global_and_v1_suppresses_everything():
    values = {
        "index_version": 1,
        "index_emo_vector": VECTOR,
        "index_emo_weight": 0.3,
        "index_role_emotions": "man.wav = 0,0,0,0,0,0,0,0",
    }
    assert index_emotion_for_role(values, "man.wav") is None
    values["index_version"] = 0
    values["index_role_emotions"] = "bad saved text"
    assert index_emotion_for_role(values, "woman.wav") is None


@pytest.fixture
def index_calls(monkeypatch, tmp_path):
    calls = []
    ref_wav = tmp_path / "ref.wav"
    ref_wav.write_bytes(b"RIFF")

    class Client:
        def predict(self, **kwargs):
            calls.append(kwargs)
            output = tmp_path / f"generated-{len(calls)}.wav"
            output.write_bytes(b"RIFF")
            return output.as_posix()

    monkeypatch.setattr(GradioBase, "get_thread_client", lambda self: Client())
    monkeypatch.setattr(
        GradioBase,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copyfile(src, dst)),
    )
    monkeypatch.setattr(
        _index.IndexTTS,
        "get_ref_wav",
        lambda self, item: (ref_wav.as_posix(), "Reference text."),
    )
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    monkeypatch.setattr(_index, "REAL_USE", _index.METHOD_TEXT_EN)
    return calls


def _lines(tmp_path, roles):
    return [
        {
            "line": number,
            "text": "Hello there.",
            "role": role,
            "filename": (tmp_path / f"line-{number}.wav").as_posix(),
        }
        for number, role in enumerate(roles, 1)
    ]


def test_index_request_uses_two_role_emotions_and_global_fallback(
    monkeypatch, tmp_path, index_calls
):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", "0,0,0.6,0,0,0,0,0")
    monkeypatch.setitem(params, "index_emo_weight", 0.3)
    monkeypatch.setitem(
        params,
        "index_role_emotions",
        f"man.wav = {VECTOR} ; 0.7\nwoman.wav = 0,0.4,0,0,0,0,0,0 ; 0.2",
    )
    tts.run(
        queue_tts=_lines(tmp_path, ["man.wav", "woman.wav", "neutral.wav"]),
        language="en",
        uuid="test-uuid",
        tts_type=tts.INDEX_TTS,
    )
    sent = {
        call["emo_weight"]: [call[f"vec{i}"] for i in range(1, 9)]
        for call in index_calls
    }
    assert sent == {
        0.7: [0.8] + [0.0] * 7,
        0.2: [0.0, 0.4] + [0.0] * 6,
        0.3: [0.0, 0.0, 0.6] + [0.0] * 5,
    }


def test_default_role_setting_keeps_request_unchanged(
    monkeypatch, tmp_path, index_calls
):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", "")
    monkeypatch.setitem(params, "index_emo_weight", 0.65)
    monkeypatch.setitem(params, "index_role_emotions", "")
    tts.run(
        queue_tts=_lines(tmp_path, ["man.wav"]),
        language="en",
        uuid="test-uuid",
        tts_type=tts.INDEX_TTS,
    )
    (request,) = index_calls
    assert request.pop("api_name") == "/gen_single"
    assert sorted(request) == ["emo_control_method", "emo_ref_path", "prompt", "text"]
    assert request["emo_control_method"] == "Same as the voice reference"


def test_bad_saved_role_emotion_stops_without_sending(
    monkeypatch, tmp_path, index_calls
):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_role_emotions", "man.wav = 0.8,0")
    with pytest.raises(StopTask, match="line 1.*exactly 8"):
        tts.run(
            queue_tts=_lines(tmp_path, ["man.wav"]),
            language="en",
            uuid="test-uuid",
            tts_type=tts.INDEX_TTS,
        )
    assert index_calls == []


def test_bad_saved_role_emotion_stops_when_output_is_cached(
    monkeypatch, tmp_path, index_calls
):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_role_emotions", "man.wav = 0.8,0")
    line = _lines(tmp_path, ["man.wav"])[0]
    Path(line["filename"]).write_bytes(b"RIFF")
    instance = _index.IndexTTS(
        queue_tts=[line],
        language="en",
        uuid="test-uuid",
        tts_type=tts.INDEX_TTS,
    )
    with pytest.raises(StopTask, match="line 1.*exactly 8"):
        instance._run(line)
    assert index_calls == []


def _srt(text):
    return f"1\n00:00:00,500 --> 00:00:02,000\n{text}\n"


def _stage_cache_key(monkeypatch, tmp_path, role_emotions):
    cache = tmp_path / "dubbing-cache"
    cache.mkdir(exist_ok=True)
    monkeypatch.setattr(_stage_dubbing, "DUBBING_CACHE", cache.as_posix())
    monkeypatch.setattr(app_cfg, "line_roles", {})
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", "")
    monkeypatch.setitem(params, "index_role_emotions", role_emotions)

    def run_tts(*, queue_tts, **kwargs):
        for item in queue_tts:
            Path(item["filename"]).write_bytes(b"RIFF")

    monkeypatch.setattr(_stage_dubbing, "run_tts", run_tts)
    root = tmp_path / f"run-{len(list(tmp_path.glob('run-*')))}"
    task = TransCreate(
        cfg=TaskCfgVTT(
            name=(root / "video.mp4").as_posix(),
            noextname="video",
            uuid="video-uuid",
            target_dir=(root / "out").as_posix(),
            cache_folder=(root / "tmp").as_posix(),
            source_language_code="en",
            target_language_code="en",
            voice_role="man.wav",
            tts_type=tts.INDEX_TTS,
        )
    )
    Path(task.cfg.target_dir).mkdir(parents=True, exist_ok=True)
    Path(task.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
    Path(task.cfg.source_sub).write_text(_srt("Hello there."), encoding="utf-8")
    Path(task.cfg.target_sub).write_text(_srt("Hello there."), encoding="utf-8")
    task.dubbing()
    return next(cache.iterdir()).name


def test_stage_cache_key_changes_with_effective_role_emotion(monkeypatch, tmp_path):
    first = _stage_cache_key(monkeypatch, tmp_path, f"man.wav = {VECTOR} ; 0.3")
    for item in (tmp_path / "dubbing-cache").iterdir():
        item.unlink()
    second = _stage_cache_key(monkeypatch, tmp_path, f"man.wav = {VECTOR} ; 0.7")
    assert first != second


def test_stage_bad_saved_role_stops_before_tts_even_with_cached_lines(
    monkeypatch, tmp_path
):
    _stage_cache_key(monkeypatch, tmp_path, "")
    called = []
    monkeypatch.setattr(
        _stage_dubbing, "run_tts", lambda **kwargs: called.append(kwargs)
    )
    with pytest.raises(StopTask, match="line 1.*exactly 8"):
        _stage_cache_key(monkeypatch, tmp_path, "man.wav = 0.8,0")
    assert called == []


def test_no_emotion_role_cache_suffix_is_identical_to_base():
    values = {
        "index_version": 1,
        "index_emo_vector": "",
        "index_emo_weight": 0.65,
        "index_role_emotions": "",
    }
    assert emotion_cache_suffix(values, "man.wav") == ""


def _subtitle_task_filename(monkeypatch, tmp_path, tts_type, role_emotions):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", "")
    monkeypatch.setitem(params, "index_role_emotions", role_emotions)
    monkeypatch.setattr(app_cfg, "dubbing_role", {})
    queued = []
    monkeypatch.setattr(tts, "run", lambda **kwargs: queued.extend(kwargs["queue_tts"]))
    source = tmp_path / f"input-{len(list(tmp_path.glob('input-*')))}.srt"
    source.write_text(_srt("Hello there."), encoding="utf-8")
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


def test_subtitle_task_index_filename_changes_with_role_emotion(monkeypatch, tmp_path):
    first = _subtitle_task_filename(
        monkeypatch, tmp_path, tts.INDEX_TTS, f"man.wav = {VECTOR} ; 0.3"
    )
    second = _subtitle_task_filename(
        monkeypatch, tmp_path, tts.INDEX_TTS, f"man.wav = {VECTOR} ; 0.7"
    )
    assert first != second


def test_subtitle_task_bad_saved_role_stops_before_tts_with_cached_line(
    monkeypatch, tmp_path
):
    cached = _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, "")
    Path(cached).parent.mkdir(parents=True, exist_ok=True)
    Path(cached).write_bytes(b"RIFF")
    monkeypatch.setattr(tts, "run", lambda **kwargs: pytest.fail("TTS was called"))
    with pytest.raises(StopTask, match="line 1.*exactly 8"):
        _subtitle_task_filename(monkeypatch, tmp_path, tts.INDEX_TTS, "man.wav = 0.8,0")


def test_subtitle_task_other_channels_do_not_read_index_emotions(monkeypatch, tmp_path):
    monkeypatch.setattr(
        dubbing,
        "emotion_cache_suffix",
        lambda *args: pytest.fail("non-Index channel read Index emotion settings"),
    )
    assert _subtitle_task_filename(monkeypatch, tmp_path, tts.OPENAI_TTS, "invalid")


def test_settings_window_loads_validates_and_saves_role_text_as_typed(
    monkeypatch, tmp_path
):
    from videotrans import winform
    from videotrans.util import ListenVoice, help_misc, help_role
    from videotrans.winform import gradiowin

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Field:
        def __init__(self, value=""):
            self.value = value
            self.clicked = Signal()

        def text(self):
            return self.value

        def setText(self, value):
            self.value = value

        def toPlainText(self):
            return self.value

        def setPlainText(self, value):
            self.value = value

        def currentIndex(self):
            return 1

        def setCurrentIndex(self, value):
            pass

        def currentText(self):
            return "v2"

        def setCurrentText(self, value):
            pass

    class Window:
        def __init__(self):
            for name in (
                "save",
                "sparktts_urltest",
                "indextts_urltest",
                "voxcpmtts_urltest",
                "firered3tts_urltest",
                "sparktts_url",
                "indextts_url",
                "indextts_emo_vector",
                "indextts_emo_weight",
                "indextts_role_emotions",
                "voxcpmtts_url",
                "firered3tts_url",
                "indextts_version",
                "voxcpmtts_version",
            ):
                setattr(self, name, Field())
            self.closed = False

        def close(self):
            self.closed = True

    started = []

    class Worker:
        def __init__(self, **kwargs):
            self.uito = Signal()

        def start(self):
            started.append(True)

    root = tmp_path / "root"
    ref_dir = root / "f5-tts"
    ref_dir.mkdir(parents=True)
    (ref_dir / "man.wav").write_bytes(b"RIFF")
    errors = []
    monkeypatch.setattr(config, "ROOT_DIR", root.as_posix())
    monkeypatch.setattr(winform, "get_cls", lambda name: Window)
    monkeypatch.setattr(help_misc, "set_process", lambda **kwargs: None)
    monkeypatch.setattr(help_misc, "show_error", errors.append)
    monkeypatch.setattr(
        help_role,
        "get_f5tts_role",
        lambda: {"man.wav": {"ref_wav": "man.wav"}},
    )
    monkeypatch.setattr(ListenVoice, "ListenVoice", Worker)
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setitem(params, "index_emo_vector", "")
    monkeypatch.setitem(params, "index_emo_weight", 0.65)
    monkeypatch.setitem(params, "index_role_emotions", f"man.wav = {VECTOR}")

    window = gradiowin.openwin()
    assert window.indextts_role_emotions.toPlainText() == f"man.wav = {VECTOR}"

    window.indextts_role_emotions.setPlainText("man.wav = 0.8,0")
    window.save.clicked.callback()
    window.indextts_urltest.clicked.callback()
    assert len(errors) == 2
    assert all("line 1" in error for error in errors)
    assert started == []
    assert not window.closed

    typed = f"# keep this comment\n\nwoman.wav＝{VECTOR}；.7   \n"
    window.indextts_role_emotions.setPlainText(typed)
    window.indextts_urltest.clicked.callback()
    expected = f"# keep this comment\n\nwoman.wav＝{VECTOR}；.7"
    assert params["index_role_emotions"] == expected
    assert window.indextts_role_emotions.toPlainText() == typed
    assert started == [True]

    window.save.clicked.callback()
    assert window.closed
