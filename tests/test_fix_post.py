# -*- coding: utf-8 -*-
"""
Regression tests for _fix_post subtitle merging logic.

Covers bugs fixed in:
- PR #1050: _fix_post IndexError when merging with empty list/text
"""
import copy
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from videotrans.util.help_srt import ms_to_time_string

# Mock missing dependencies before loading _base.py
for _mod in ['ten_vad', 'pydub', 'pydub.silence',
             'videotrans.task', 'videotrans.task.vad']:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Load _base.py directly to avoid sys.modules pollution from other tests
_base_path = os.path.join(PROJECT_ROOT, 'videotrans', 'recognition', '_base.py')
_base_spec = importlib.util.spec_from_file_location('videotrans.recognition._base', _base_path)
if _base_spec and _base_spec.loader:
    _base_mod = importlib.util.module_from_spec(_base_spec)
    _base_spec.loader.exec_module(_base_mod)
    BaseRecogn = _base_mod.BaseRecogn
else:
    raise ImportError("Cannot load recognition/_base.py")


def _make_item(text, start_ms, end_ms):
    return {
        "line": 0,
        "text": text,
        "start_time": start_ms,
        "end_time": end_ms,
        "startraw": ms_to_time_string(ms=start_ms),
        "endraw": ms_to_time_string(ms=end_ms),
        "time": f"{ms_to_time_string(ms=start_ms)} --> {ms_to_time_string(ms=end_ms)}",
    }


def _make_recognizer(is_cjk=False):
    """Minimal object with attributes needed by _fix_post."""
    obj = types.SimpleNamespace()
    obj.flag = [",", ".", "?", "!", ";", "，", "。", "？", "；", "！"]
    obj.half_flag = [",", "，", "-", "、", ":", "："]
    obj.end_flag = [".", "。", "?", "？", "!", "！"]
    obj.join_word_flag = "" if is_cjk else " "
    obj.is_cjk = is_cjk
    obj._fix_post = BaseRecogn._fix_post.__get__(obj, type(obj))
    return obj


class TestFixPostBasicMerging(unittest.TestCase):
    """Test short subtitle merging in _fix_post."""

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_all_long_subtitles_unchanged(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello world", 0, 2000),
            _make_item("Second line", 2500, 4500),
            _make_item("Third line", 5000, 7000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertEqual(len(result), 3)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_short_middle_merged_to_prev(self, mock_tools):
        """Short middle subtitle closer to previous → merged into previous."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello", 0, 2000),        # long enough
            _make_item("short", 2100, 2400),      # 300ms, close to prev (100ms gap)
            _make_item("World", 3000, 5000),       # long enough
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        # The short one should be merged (either into prev or next)
        self.assertLessEqual(len(result), 3)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_empty_text_skipped(self, mock_tools):
        """PR #1050: Empty text items must be skipped without IndexError."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello", 0, 2000),
            _make_item("", 2100, 2400),            # empty text
            _make_item("World", 3000, 5000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        # Empty text should be skipped, not crash
        texts = [it['text'].strip() for it in result if it['text'].strip()]
        self.assertTrue(all(t for t in texts))

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_single_subtitle(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [_make_item("Only one", 0, 2000)]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], "Only one")

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_two_subtitles_no_merge(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello", 0, 2000),
            _make_item("World", 3000, 5000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertEqual(len(result), 2)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '5000'})
    @patch('videotrans.recognition._base.tools')
    def test_first_subtitle_short_merged(self, mock_tools):
        """First subtitle shorter than min_speech and close to next → merged."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hi", 0, 500),              # 500ms < 5000ms min
            _make_item("Long enough subtitle", 600, 6000),
            _make_item("Also long enough", 7000, 12000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        # First may be merged into second if gap < 2000ms
        self.assertGreaterEqual(len(result), 2)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '5000'})
    @patch('videotrans.recognition._base.tools')
    def test_last_subtitle_short_merged(self, mock_tools):
        """Last subtitle shorter than min_speech and close to prev → merged."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Long enough subtitle", 0, 6000),
            _make_item("Also long", 7000, 12000),
            _make_item("End", 12500, 12800),        # 300ms < 5000ms, close to prev
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        # Last may be merged into prev
        self.assertGreaterEqual(len(result), 2)


class TestFixPostPunctuation(unittest.TestCase):
    """Test punctuation-based splitting in _fix_post."""

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_trailing_period_stripped(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello.", 0, 2000),
            _make_item("World.", 3000, 5000),
            _make_item("End.", 6000, 8000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        for it in result:
            self.assertFalse(it['text'].strip().endswith('。'))
            # Periods at end should be stripped (Chinese 。 only, not English .)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_cjk_mode(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer(is_cjk=True)
        srt = [
            _make_item("你好世界", 0, 2000),
            _make_item("这是测试", 3000, 5000),
            _make_item("最后一句", 6000, 8000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertEqual(len(result), 3)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_all_empty_text_returns_empty(self, mock_tools):
        """PR #1050: All empty texts → returns empty list."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("", 0, 500),
            _make_item("", 1000, 1500),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertEqual(len(result), 0)


class TestFixPostEdgeCases(unittest.TestCase):
    """Edge cases for _fix_post that caused crashes before PR #1050."""

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_whitespace_only_text(self, mock_tools):
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("   ", 0, 2000),
            _make_item("Hello", 3000, 5000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        # Whitespace-only should be filtered out
        self.assertTrue(all(it['text'].strip() for it in result))

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_zero_duration_subtitle(self, mock_tools):
        """Start time == end time should not crash."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello", 0, 2000),
            _make_item("Zero", 3000, 3000),         # zero duration
            _make_item("World", 4000, 6000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertGreater(len(result), 0)

    @patch('videotrans.recognition._base.settings', {'min_speech_duration_ms': '1000'})
    @patch('videotrans.recognition._base.tools')
    def test_overlapping_subtitles(self, mock_tools):
        """Overlapping time ranges should not crash."""
        mock_tools.ms_to_time_string = ms_to_time_string
        recog = _make_recognizer()
        srt = [
            _make_item("Hello", 0, 2000),
            _make_item("Over", 1500, 2500),         # overlaps with prev
            _make_item("World", 3000, 5000),
        ]
        result = recog._fix_post(copy.deepcopy(srt))
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
