# -*- coding: utf-8 -*-
"""
Regression tests for videotrans/util/help_srt.py

Covers bugs fixed in:
- PR #1036: UTF-8 BOM SRT parsing
- PR #1042: simple_wrap IndexError
- PR #1048: format_time / ms_to_time_string edge cases
"""
import os
import tempfile
import unittest

from videotrans.util.help_srt import (
    ms_to_time_string,
    format_time,
    simple_wrap,
    get_subtitle_from_srt,
)


class TestMsToTimeString(unittest.TestCase):
    """Regression tests for ms_to_time_string (pure function)."""

    def test_zero(self):
        self.assertEqual(ms_to_time_string(ms=0), "00:00:00,000")

    def test_milliseconds_only(self):
        self.assertEqual(ms_to_time_string(ms=500), "00:00:00,500")

    def test_seconds(self):
        self.assertEqual(ms_to_time_string(ms=3000), "00:00:03,000")

    def test_minutes(self):
        self.assertEqual(ms_to_time_string(ms=65000), "00:01:05,000")

    def test_hours(self):
        self.assertEqual(ms_to_time_string(ms=3661500), "01:01:01,500")

    def test_custom_separator(self):
        self.assertEqual(ms_to_time_string(ms=1500, sepflag='.'), "00:00:01.500")

    def test_from_seconds_param(self):
        self.assertEqual(ms_to_time_string(seconds=90), "00:01:30,000")

    def test_large_milliseconds(self):
        result = ms_to_time_string(ms=86399999)
        self.assertEqual(result, "23:59:59,999")

    def test_one_day_wraps(self):
        # timedelta(days=1) has .seconds=0
        result = ms_to_time_string(ms=86400000)
        self.assertEqual(result, "00:00:00,000")


class TestFormatTime(unittest.TestCase):
    """Regression tests for format_time."""

    def test_empty_string(self):
        self.assertEqual(format_time(""), "00:00:00,000")

    def test_standard_srt_format(self):
        self.assertEqual(format_time("01:02:03,456"), "01:02:03,456")

    def test_dot_separator_input(self):
        result = format_time("01:02:03.456")
        self.assertEqual(result, "01:02:03,456")

    def test_custom_output_separator(self):
        result = format_time("01:02:03,456", separate='.')
        self.assertEqual(result, "01:02:03.456")

    def test_leading_zeros_in_hours(self):
        result = format_time("001:01:2,4500")
        # int("4500") -> f"4500"[-3:] -> "500"
        self.assertEqual(result, "01:01:02,500")

    def test_two_component_time(self):
        result = format_time("01:54,14")
        self.assertEqual(result, "00:01:54,014")

    def test_seconds_only(self):
        result = format_time("45,500")
        self.assertEqual(result, "00:00:45,500")

    def test_no_milliseconds(self):
        result = format_time("01:02:03")
        self.assertEqual(result, "01:02:03,000")

    def test_whitespace_padded(self):
        result = format_time(" 01 : 02 : 03 , 456 ")
        self.assertEqual(result, "01:02:03,456")


class TestSimpleWrap(unittest.TestCase):
    """Regression tests for simple_wrap.

    PR #1042 fixed IndexError when offset lookahead goes out of bounds.
    """

    def test_short_text_unchanged(self):
        text = "Hello"
        self.assertEqual(simple_wrap(text, maxlen=15), text)

    def test_empty_string(self):
        self.assertEqual(simple_wrap("", maxlen=15), "")

    def test_short_text_below_threshold(self):
        text = "This is a test"
        self.assertEqual(simple_wrap(text, maxlen=15), text)

    def test_long_text_with_punctuation(self):
        text = "Hello world, this is a test of the wrapping function."
        result = simple_wrap(text, maxlen=15)
        for line in result.split('\n'):
            self.assertLessEqual(len(line), 20, f"Line too long: '{line}'")

    def test_long_text_no_punctuation(self):
        text = "abcdefghijklmnopqrstuvwx"
        result = simple_wrap(text, maxlen=10)
        self.assertTrue(len(result) > 0)

    def test_chinese_text(self):
        text = "这是一段中文文本用来测试换行功能是否正常工作"
        result = simple_wrap(text, maxlen=10, language="zh")
        lines = result.split('\n')
        self.assertGreater(len(lines), 1)

    def test_maxlen_minimum(self):
        text = "abcdefghij"
        result = simple_wrap(text, maxlen=3)
        self.assertTrue(len(result) > 0)

    def test_single_character(self):
        self.assertEqual(simple_wrap("A", maxlen=15), "A")

    def test_whitespace_only(self):
        result = simple_wrap("   ", maxlen=15)
        self.assertEqual(result, "")

    def test_exact_maxlen_boundary(self):
        text = "a" * 15
        result = simple_wrap(text, maxlen=15)
        self.assertEqual(result, text)

    def test_just_over_maxlen(self):
        # PR #1042 regression: offset lookahead must not IndexError
        text = "a" * 20
        result = simple_wrap(text, maxlen=15)
        self.assertTrue(len(result) > 0)

    def test_japanese_text(self):
        text = "これは日本語のテストです。 wrapping をテストしています。"
        result = simple_wrap(text, maxlen=12, language="ja")
        self.assertTrue(len(result) > 0)

    def test_all_punctuation(self):
        text = "，。！？，。！？，。"
        result = simple_wrap(text, maxlen=5, language="zh")
        self.assertIsNotNone(result)


class TestGetSubtitleFromSrt(unittest.TestCase):
    """Regression tests for get_subtitle_from_srt.

    PR #1036: UTF-8 BOM handling.
    """

    def _write_srt(self, content, encoding='utf-8'):
        f = tempfile.NamedTemporaryFile(mode='wb', suffix='.srt', delete=False)
        f.write(content.encode(encoding) if isinstance(content, str) else content)
        f.close()
        return f.name

    def test_valid_srt_string(self):
        srt_content = "1\n00:00:01,000 --> 00:00:02,000\nHello World\n\n"
        result = get_subtitle_from_srt(srt_content, is_file=False)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'Hello World')
        self.assertEqual(result[0]['start_time'], 1000)
        self.assertEqual(result[0]['end_time'], 2000)

    def test_multi_subtitle_srt(self):
        srt_content = (
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n"
            "2\n00:00:03,000 --> 00:00:04,000\nWorld\n\n"
        )
        result = get_subtitle_from_srt(srt_content, is_file=False)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['text'], 'Hello')
        self.assertEqual(result[1]['text'], 'World')

    def test_empty_content_raises(self):
        with self.assertRaises(RuntimeError):
            get_subtitle_from_srt("", is_file=False)

    def test_plain_text_fallback(self):
        result = get_subtitle_from_srt("Just some plain text", is_file=False)
        self.assertEqual(len(result), 1)
        # Plain text is split into individual lines by the SRT parser
        self.assertTrue(len(result[0]['text']) > 0)

    def test_utf8_bom_file(self):
        """PR #1036: SRT file with UTF-8 BOM should parse."""
        srt_content = "1\n00:00:01,000 --> 00:00:02,000\nBOM test\n\n"
        bom_content = b'\xef\xbb\xbf' + srt_content.encode('utf-8')
        path = self._write_srt(bom_content)
        try:
            result = get_subtitle_from_srt(path, is_file=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['text'], 'BOM test')
        finally:
            os.unlink(path)

    def test_gbk_file(self):
        srt_content = "1\n00:00:01,000 --> 00:00:02,000\n中文测试\n\n"
        path = self._write_srt(srt_content, encoding='gbk')
        try:
            result = get_subtitle_from_srt(path, is_file=True)
            self.assertEqual(len(result), 1)
            self.assertIn("中文测试", result[0]['text'])
        finally:
            os.unlink(path)

    def test_srt_with_dot_separator(self):
        srt_content = "1\n00:00:01.000 --> 00:00:02.000\nDot separator\n\n"
        result = get_subtitle_from_srt(srt_content, is_file=False)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'Dot separator')


if __name__ == '__main__':
    unittest.main()
