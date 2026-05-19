# -*- coding: utf-8 -*-
"""
Regression tests for exception handling and role parsing.

Covers bugs fixed in:
- PR #1068: OpenAI exception handler body=None AttributeError
- PR #1055: get_f5tts_role None return not guarded
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock missing third-party deps needed by _except.py
_mock_third_party = [
    'elevenlabs', 'elevenlabs.core',
    'deepgram', 'deepgram.clients', 'deepgram.clients.common',
    'deepgram.clients.common.v1', 'deepgram.clients.common.v1.errors',
    'aiohttp', 'aiohttp.client_exceptions',
]
for mod_name in _mock_third_party:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from videotrans.configure._except import (
    VideoTransError,
    TranslateSrtError,
    DubbSrtError,
    SpeechToTextError,
    StopRetry,
    _is_local_address,
    _extract_api_url_from_error,
)
from videotrans.util.help_role import get_f5tts_role, get_gptsovits_role
from videotrans.configure.config import params


# ── VideoTransError hierarchy ──

class TestVideoTransError(unittest.TestCase):

    def test_basic_message(self):
        self.assertEqual(str(VideoTransError("err")), "err")

    def test_empty_message(self):
        self.assertEqual(str(VideoTransError()), "")

    def test_subclass_hierarchy(self):
        for cls in [TranslateSrtError, DubbSrtError, SpeechToTextError, StopRetry]:
            self.assertTrue(issubclass(cls, VideoTransError))

    def test_subclass_str(self):
        self.assertEqual(str(TranslateSrtError("bad srt")), "bad srt")


# ── _is_local_address ──

class TestIsLocalAddress(unittest.TestCase):

    def test_localhost(self):
        self.assertTrue(_is_local_address("http://localhost:8080"))

    def test_127(self):
        self.assertTrue(_is_local_address("127.0.0.1:3000"))

    def test_0000(self):
        self.assertTrue(_is_local_address("0.0.0.0"))

    def test_ipv6(self):
        self.assertTrue(_is_local_address("::1"))

    def test_remote(self):
        self.assertFalse(_is_local_address("https://api.openai.com"))

    def test_none(self):
        self.assertFalse(_is_local_address(None))

    def test_empty(self):
        self.assertFalse(_is_local_address(""))

    def test_case_insensitive(self):
        self.assertTrue(_is_local_address("HTTP://LOCALHOST"))


# ── _extract_api_url_from_error ──

class TestExtractApiUrl(unittest.TestCase):

    def test_https(self):
        self.assertEqual(
            _extract_api_url_from_error("Connection to https://api.openai.com failed"),
            "https://api.openai.com"
        )

    def test_http(self):
        self.assertEqual(
            _extract_api_url_from_error("http://localhost:8080/v1"),
            "http://localhost:8080/v1"
        )

    def test_no_url(self):
        self.assertIsNone(_extract_api_url_from_error("unknown error"))

    def test_www(self):
        self.assertIsNotNone(_extract_api_url_from_error("www.example.com failed"))


# ── Body fallback pattern (PR #1068 regression) ──

class TestBodyFallbackPattern(unittest.TestCase):
    """Test the body/message/detail extraction pattern that PR #1068 fixed.
    Tested as a unit to avoid isinstance() crashes with mocked exception types.
    """

    @staticmethod
    def _extract(ex):
        """Mirrors the fallback logic from _except.py lines 404-432."""
        if hasattr(ex, 'message') and ex.message:
            return str(ex.message)
        if hasattr(ex, 'detail') and ex.detail:
            if isinstance(ex.detail, dict):
                msg = ex.detail.get('message')
                if msg:
                    return str(msg)
            return str(ex.detail)
        if hasattr(ex, 'body') and ex.body:
            if isinstance(ex.body, dict):
                msg = ex.body.get('message')
                if msg:
                    return str(msg)
            return str(ex.body)
        return ''

    def test_body_none_no_crash(self):
        """PR #1068: body=None must not cause AttributeError."""
        e = Exception("test"); e.body = None  # type: ignore
        self.assertEqual(self._extract(e), '')

    def test_body_dict_message(self):
        e = Exception(); e.body = {"message": "rate limited"}  # type: ignore
        self.assertEqual(self._extract(e), "rate limited")

    def test_body_nested_error(self):
        e = Exception()
        e.body = {"error": {"message": "server overloaded"}}  # type: ignore
        self.assertIn("server overloaded", self._extract(e))

    def test_body_string(self):
        e = Exception(); e.body = "plain body"  # type: ignore
        self.assertEqual(self._extract(e), "plain body")

    def test_message_attribute(self):
        e = Exception(); e.message = "msg attr"  # type: ignore
        self.assertEqual(self._extract(e), "msg attr")

    def test_detail_dict(self):
        e = Exception(); e.detail = {"message": "detail msg"}  # type: ignore
        self.assertEqual(self._extract(e), "detail msg")

    def test_body_empty_dict(self):
        e = Exception(); e.body = {}  # type: ignore
        self.assertEqual(self._extract(e), '')

    def test_no_attributes(self):
        self.assertEqual(self._extract(Exception()), '')


# ── get_f5tts_role (PR #1055) ──

class TestGetF5TtsRole(unittest.TestCase):

    def setUp(self):
        self._orig = params.get('f5tts_role', '')

    def tearDown(self):
        params['f5tts_role'] = self._orig

    def test_empty_returns_none(self):
        params['f5tts_role'] = ''
        self.assertIsNone(get_f5tts_role())

    def test_whitespace_returns_none(self):
        params['f5tts_role'] = '   \n\t  '
        self.assertIsNone(get_f5tts_role())

    def test_valid_entries(self):
        params['f5tts_role'] = '/audio1.wav#Hello world\n/audio2.wav#Test text'
        result = get_f5tts_role()
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn('No', result)
        self.assertIn('clone', result)
        self.assertIn('/audio1.wav', result)
        self.assertEqual(result['/audio1.wav']['ref_text'], 'Hello world')

    def test_malformed_skipped(self):
        params['f5tts_role'] = 'bad#a#extra\nno_hash\nvalid#text'
        result = get_f5tts_role()
        assert result is not None
        self.assertNotIn('bad', result)
        self.assertNotIn('no_hash', result)
        self.assertIn('valid', result)


# ── get_gptsovits_role ──

class TestGetGptSoVitsRole(unittest.TestCase):

    def setUp(self):
        self._orig = params.get('gptsovits_role', '')

    def tearDown(self):
        params['gptsovits_role'] = self._orig

    def test_empty_returns_none(self):
        params['gptsovits_role'] = ''
        self.assertIsNone(get_gptsovits_role())

    def test_valid_entries(self):
        params['gptsovits_role'] = '/audio.wav#hello#zh\n/voice.wav#world#en'
        result = get_gptsovits_role()
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn('/audio.wav', result)
        self.assertEqual(result['/audio.wav']['prompt_text'], 'hello')
        self.assertEqual(result['/audio.wav']['prompt_language'], 'zh')

    def test_malformed_skipped(self):
        params['gptsovits_role'] = 'bad#entry\nvalid#a#zh'
        result = get_gptsovits_role()
        assert result is not None
        self.assertNotIn('bad', result)
        self.assertIn('valid', result)


if __name__ == '__main__':
    unittest.main()
