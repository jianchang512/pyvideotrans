"""Audexum recognition channel: request shape, SrtItem mapping and error handling. HTTP is mocked."""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import APIStatusError

from videotrans import get_class
from videotrans.configure.config import params
from videotrans.configure.excepts import StopTask
from videotrans.recognition import AUDEXUM_API, ID_NAME_DICT, is_allow_lang
from videotrans.recognition import _audexum
from videotrans.recognition._audexum import AudexumRecogn, AUDEXUM_BASE_URL


def _clips(tmp_path, n=2):
    raws = []
    for i in range(n):
        f = tmp_path / f"audio_{i}.wav"
        f.write_bytes(b"RIFF" + bytes(2048))
        raws.append({"line": i + 1, "text": "", "start_time": i * 1000, "end_time": i * 1000 + 900,
                     "startraw": "", "endraw": "", "time": "", "filename": str(f)})
    return raws


def _status_error(code, body):
    req = httpx.Request("POST", AUDEXUM_BASE_URL + "/audio/transcriptions")
    resp = httpx.Response(code, request=req, json=body)
    return APIStatusError(f"Error code: {code}", response=resp, body=body)


@pytest.fixture
def key():
    old = params.get("audexum_key", "")
    params["audexum_key"] = "sk_test_x"
    yield
    params["audexum_key"] = old


def _run(tmp_path, create, detect_language="bg", n=2):
    rec = AudexumRecogn(detect_language=detect_language, recogn_type=AUDEXUM_API)
    with patch.object(AudexumRecogn, "cut_audio", return_value=_clips(tmp_path, n)), \
            patch.object(AudexumRecogn, "_exit", return_value=False), \
            patch.object(_audexum, "OpenAI") as openai_cls:
        openai_cls.return_value.audio.transcriptions.create.side_effect = create
        return rec._exec(), openai_cls


def test_registered():
    assert ID_NAME_DICT[AUDEXUM_API].key_name == "audexum_key"
    assert get_class(AUDEXUM_API, "recognition", ID_NAME_DICT) is AudexumRecogn
    assert is_allow_lang("bg", AUDEXUM_API) is True


def test_request_shape_and_srt_mapping(tmp_path, key):
    create = MagicMock(side_effect=[MagicMock(text=" Добър ден. "), MagicMock(text="Как сте?")])
    res, openai_cls = _run(tmp_path, create, detect_language="bg")
    kw = openai_cls.call_args.kwargs
    assert kw["base_url"] == "https://audexum.com/v1"
    assert kw["api_key"] == "sk_test_x"
    assert create.call_count == 2
    call = create.call_args_list[0].kwargs
    assert call["model"] == "whisper-1"
    assert call["language"] == "bg"
    assert call["response_format"] == "json"
    assert call["file"][0] == "audio_0.wav"
    assert "prompt" not in call
    assert [it["text"] for it in res] == ["Добър ден.", "Как сте?"]
    assert res[1]["start_time"] == 1000 and res[1]["end_time"] == 1900


def test_auto_language_is_omitted(tmp_path, key):
    create = MagicMock(return_value=MagicMock(text="x"))
    _run(tmp_path, create, detect_language="auto", n=1)
    assert "language" not in create.call_args.kwargs


def test_empty_text_is_dropped(tmp_path, key):
    create = MagicMock(side_effect=[MagicMock(text=""), MagicMock(text="да")])
    res, _ = _run(tmp_path, create)
    assert [it["text"] for it in res] == ["да"]


def test_missing_key_stops(tmp_path):
    params["audexum_key"] = ""
    with pytest.raises(StopTask):
        _run(tmp_path, MagicMock())


def test_no_speech_clip_is_skipped(tmp_path, key):
    create = MagicMock(side_effect=[_status_error(400, {"detail": "no_speech_detected"}), MagicMock(text="да")])
    res, _ = _run(tmp_path, create)
    assert [it["text"] for it in res] == ["да"]


def test_invalid_key_stops(tmp_path, key):
    create = MagicMock(side_effect=_status_error(401, {"detail": "authentication_required"}))
    with pytest.raises(StopTask, match="audexum.com/developer"):
        _run(tmp_path, create)


@pytest.mark.parametrize("code,body", [
    (402, {"detail": {"error": "insufficient_credits", "requested": 3, "upgrade_url": "/pricing"}}),
    (429, {"detail": {"error": "stt_quota_exceeded", "upgrade_url": "/pricing"}}),
])
def test_out_of_credits_tells_user_to_top_up(tmp_path, key, code, body):
    create = MagicMock(side_effect=_status_error(code, body))
    with pytest.raises(StopTask, match="audexum.com/pricing"):
        _run(tmp_path, create)
