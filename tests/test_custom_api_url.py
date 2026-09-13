import sys
from unittest.mock import MagicMock

import pytest

from videotrans.configure.config import params
from videotrans.task.taskcfg import SrtItem

for _mod in ("gradio_client",):
    try:
        __import__(_mod)
    except ImportError:
        sys.modules[_mod] = MagicMock()

from videotrans.recognition._stt import SttAPIRecogn
from videotrans.translator._transapi import TransAPI
from videotrans.tts._ttsapi import TTSAPI


def _make_srt_item(text):
    return SrtItem(
        text=text, line=1, start_time=0, end_time=1000,
        startraw="00:00:00,000", endraw="00:00:01,000",
        time="00:00:00,000 --> 00:00:01,000",
    )


@pytest.fixture
def custom_url(monkeypatch):
    def _set(key, value):
        monkeypatch.setitem(params, key, value)
    return _set


class TestCustomApiUrlKeepsCase:
    def test_transapi(self, custom_url):
        custom_url("trans_api_url", "HTTPS://Example.com/Translate?token=AbC")
        api = TransAPI(text_list=[_make_srt_item("hello")])
        assert api.api_url == "HTTPS://Example.com/Translate?token=AbC&"

    def test_transapi_without_scheme(self, custom_url):
        custom_url("trans_api_url", "127.0.0.1:9911/Translate")
        api = TransAPI(text_list=[_make_srt_item("hello")])
        assert api.api_url == "http://127.0.0.1:9911/Translate/?"

    def test_ttsapi(self, custom_url):
        custom_url("ttsapi_url", "HTTPS://Example.com/Api/TTS?key=AbC")
        tts = TTSAPI(queue_tts=[{"text": "hello"}])
        assert tts.api_url == "HTTPS://Example.com/Api/TTS?key=AbC"

    def test_ttsapi_without_scheme(self, custom_url):
        custom_url("ttsapi_url", "127.0.0.1:9000/TTS")
        tts = TTSAPI(queue_tts=[{"text": "hello"}])
        assert tts.api_url == "http://127.0.0.1:9000/TTS"

    def test_stt(self, custom_url):
        custom_url("stt_url", "HTTPS://Example.com/Whisper")
        rec = SttAPIRecogn(detect_language="en")
        assert rec.api_url == "HTTPS://Example.com/Whisper/api"

    def test_stt_without_scheme(self, custom_url):
        custom_url("stt_url", "127.0.0.1:9977/api")
        rec = SttAPIRecogn(detect_language="en")
        assert rec.api_url == "http://127.0.0.1:9977/api"
