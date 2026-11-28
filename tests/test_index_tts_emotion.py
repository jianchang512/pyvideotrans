import shutil
import sys
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, params
from videotrans.configure.excepts import StopTask

for _mod in ("gradio_client",):
    try:
        __import__(_mod)
    except ImportError:
        sys.modules[_mod] = MagicMock()

from videotrans.tts import _index
from videotrans.tts._gradio import GradioBase
from videotrans.tts._index_emotion import (
    emotion_cache_suffix,
    index_emotion,
    parse_emo_vector,
    parse_emo_weight,
)
from videotrans.util.help_misc import vail_file


@pytest.fixture
def sent(monkeypatch, tmp_path):
    calls = []

    class Client:
        def predict(self, **kwargs):
            calls.append(kwargs)
            wav = tmp_path / f"generated-{len(calls)}.wav"
            wav.write_bytes(b"RIFF")
            return wav.as_posix()

    monkeypatch.setattr(GradioBase, "get_thread_client", lambda self: Client())
    monkeypatch.setattr(
        GradioBase,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copyfile(src, dst)),
    )
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    monkeypatch.setattr(_index, "REAL_USE", _index.METHOD_TEXT_EN)
    return calls


def _line(tmp_path):
    ref_wav = tmp_path / "ref.wav"
    ref_wav.write_bytes(b"RIFF")
    return {
        "line": 1,
        "text": "Hello there.",
        "role": "clone",
        "filename": (tmp_path / "line.wav").as_posix(),
        "ref_wav": ref_wav.as_posix(),
        "ref_text": "The reference text.",
    }


def _dub(tmp_path, sent):
    line = _line(tmp_path)
    tts.run(
        queue_tts=[line],
        language="en",
        uuid="test-uuid",
        tts_type=tts.INDEX_TTS,
    )
    assert vail_file(line["filename"])
    return line, sent


@pytest.mark.parametrize("version", [1, 2], ids=["V2", "V2.5"])
def test_vector_is_sent_to_index_v2_versions(monkeypatch, tmp_path, sent, version):
    vector = [0.8, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    monkeypatch.setitem(params, "index_version", version)
    monkeypatch.setitem(params, "index_emo_vector", ",".join(map(str, vector)))
    monkeypatch.setitem(params, "index_emo_weight", 0.4)

    line, calls = _dub(tmp_path, sent)

    (request,) = calls
    assert request["emo_control_method"] == "Use emotion vectors"
    assert [request[f"vec{i}"] for i in range(1, 9)] == vector
    assert request["emo_weight"] == 0.4
    assert "emo_ref_path" in request
    assert request.get("lang_choice") == ("EN" if version == 2 else None)
    assert line["ref_wav"]


def test_v1_ignores_saved_emotion_vector(monkeypatch, tmp_path, sent):
    monkeypatch.setitem(params, "index_version", 0)
    monkeypatch.setitem(params, "index_emo_vector", "0.8,0,0,0,0,0,0,0")
    monkeypatch.setitem(params, "index_emo_weight", 0.4)

    _, calls = _dub(tmp_path, sent)

    (request,) = calls
    assert request.pop("api_name") == "/gen_single"
    assert sorted(request) == ["prompt", "text"]


@pytest.mark.parametrize("vector", ["", "0,0,0,0,0,0,0,0"], ids=["empty", "zeros"])
def test_no_vector_keeps_the_existing_v2_request(monkeypatch, tmp_path, sent, vector):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", vector)
    monkeypatch.setitem(params, "index_emo_weight", 0.4)

    _, calls = _dub(tmp_path, sent)

    (request,) = calls
    assert request.pop("api_name") == "/gen_single"
    assert sorted(request) == [
        "emo_control_method",
        "emo_ref_path",
        "prompt",
        "text",
    ]
    assert request["emo_control_method"] == "Same as the voice reference"


def test_chinese_ui_retry_uses_chinese_vector_label(monkeypatch, tmp_path, sent):
    calls = []

    class Client:
        def predict(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise ValueError(
                    "Use emotion vectors is not in choices: 与音色参考音频相同, "
                    "使用情感参考音频, 使用情感向量控制"
                )
            wav = tmp_path / "generated.wav"
            wav.write_bytes(b"RIFF")
            return wav.as_posix()

    monkeypatch.setattr(GradioBase, "get_thread_client", lambda self: Client())
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", "0.8,0,0,0,0,0,0,0")
    monkeypatch.setitem(params, "index_emo_weight", 0.65)

    line = _line(tmp_path)
    tts.run(
        queue_tts=[line],
        language="en",
        uuid="test-uuid",
        tts_type=tts.INDEX_TTS,
    )

    assert vail_file(line["filename"])
    assert [call["emo_control_method"] for call in calls] == [
        "Use emotion vectors",
        "使用情感向量控制",
    ]


def test_parse_vector_accepts_spaces_chinese_separators_and_one_trailing_separator():
    assert parse_emo_vector(" 0.8， 0 ，0， 0，0，0，0，0 ") == [
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    assert parse_emo_vector("0.8、0、0、0、0、0、0、0、") == [
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    assert parse_emo_vector("0.8,0,0,0,0,0,0,0,") == [
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    assert parse_emo_vector(None) is None


@pytest.mark.parametrize(
    "value, message",
    [
        ("0,0", "exactly 8"),
        ("happy,0,0,0,0,0,0,0", "only numbers"),
        ("0.8,,0,0,0,0,0,0", "only numbers"),
        ("-0.1,0,0,0,0,0,0,0", "between 0 and 1"),
        ("1.1,0,0,0,0,0,0,0", "between 0 and 1"),
        ("nan,0,0,0,0,0,0,0", "between 0 and 1"),
        ("inf,0,0,0,0,0,0,0", "between 0 and 1"),
    ],
)
def test_parse_vector_rejects_invalid_values(value, message):
    with pytest.raises(ValueError, match=message):
        parse_emo_vector(value)


def test_parse_weight_default_and_bounds():
    assert parse_emo_weight(0) == 0
    assert parse_emo_weight(1) == 1
    assert parse_emo_weight("") == 0.65
    assert parse_emo_weight(None) == 0.65
    for value in ("-0.1", "1.1", "nan", "inf"):
        with pytest.raises(ValueError, match="between 0 and 1"):
            parse_emo_weight(value)
    with pytest.raises(ValueError, match="must be a number"):
        parse_emo_weight("heavy")


@pytest.mark.parametrize(
    "vector, weight, message",
    [
        ("0.8,0", 0.65, "exactly 8"),
        ("0.8,0,0,0,0,0,0,0", "heavy", "weight must be a number"),
    ],
    ids=["vector", "weight"],
)
def test_invalid_saved_emotion_stops_the_task_without_sending(
    monkeypatch, tmp_path, sent, vector, weight, message
):
    monkeypatch.setitem(params, "index_version", 1)
    monkeypatch.setitem(params, "index_emo_vector", vector)
    monkeypatch.setitem(params, "index_emo_weight", weight)
    line = _line(tmp_path)

    with pytest.raises(StopTask, match=message):
        tts.run(
            queue_tts=[line],
            language="en",
            uuid="test-uuid",
            tts_type=tts.INDEX_TTS,
        )

    assert not vail_file(line["filename"])
    assert sent == []


@pytest.mark.parametrize(
    "version, vector",
    [
        (0, "0.8,0,0,0,0,0,0,0"),
        (1, ""),
        (1, "0,0,0,0,0,0,0,0"),
    ],
    ids=["v1", "empty", "zeros"],
)
def test_index_emotion_and_cache_suffix_are_empty_when_no_emotion_is_sent(
    version, vector
):
    values = {
        "index_version": version,
        "index_emo_vector": vector,
        "index_emo_weight": "0.4",
    }
    assert index_emotion(values) is None
    assert emotion_cache_suffix(values) == ""


def test_index_emotion_and_cache_suffix_include_v2_vector_and_weight():
    values = {
        "index_version": 1,
        "index_emo_vector": "0.8,0,0,0,0,0,0,0",
        "index_emo_weight": "0.4",
    }
    assert index_emotion(values) == ([0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.4)
    assert emotion_cache_suffix(values) == "-0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0-0.4"


def test_shared_window_only_validates_and_saves_emotion_for_index_test(
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
                "voxcpmtts_url",
                "firered3tts_url",
                "indextts_version",
                "voxcpmtts_version",
            ):
                setattr(self, name, Field())

        def close(self):
            pass

    started = []

    class Worker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.uito = Signal()

        def start(self):
            started.append(self.kwargs["tts_type"])

    root = tmp_path / "root"
    ref_dir = root / "f5-tts"
    ref_dir.mkdir(parents=True)
    (ref_dir / "ref.wav").write_bytes(b"RIFF")
    errors = []
    monkeypatch.setattr(config, "ROOT_DIR", root.as_posix())
    monkeypatch.setattr(winform, "get_cls", lambda name: Window)
    monkeypatch.setattr(help_misc, "set_process", lambda **kwargs: None)
    monkeypatch.setattr(help_misc, "show_error", errors.append)
    monkeypatch.setattr(
        help_role,
        "get_f5tts_role",
        lambda: {"default": {"ref_wav": "ref.wav"}},
    )
    monkeypatch.setattr(ListenVoice, "ListenVoice", Worker)
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setitem(params, "index_emo_vector", "saved-vector")
    monkeypatch.setitem(params, "index_emo_weight", "saved-weight")

    window = gradiowin.openwin()
    window.indextts_emo_vector.setText("invalid")
    window.indextts_emo_weight.setText("also-invalid")
    window.sparktts_urltest.clicked.callback()

    assert started == [tts.SPARK_TTS]
    assert errors == []
    assert params["index_emo_vector"] == "saved-vector"
    assert params["index_emo_weight"] == "saved-weight"

    window.indextts_emo_vector.setText("0.12345678901234567,0,0,0,0,0,0,0")
    window.indextts_emo_weight.setText("0.12345678901234567")
    window.indextts_urltest.clicked.callback()

    assert (
        params["index_emo_vector"] == "0.12345678901234566,0.0,0.0,0.0,0.0,0.0,0.0,0.0"
    )
    assert params["index_emo_weight"] == 0.12345678901234566
