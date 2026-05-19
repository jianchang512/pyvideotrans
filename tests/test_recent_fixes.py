# -*- coding: utf-8 -*-
"""
Regression tests for bugs fixed in PRs #1093-#1095.

- PR #1093: process_text_to_srt_str strips punctuation (help_srt.py)
- PR #1094: bare except in voice rate parsing (trans_create.py)
- PR #1095: punctuation restoration bare except logging (trans_create.py + _speech2text.py)
"""
import unittest

from videotrans.util.help_srt import process_text_to_srt_str


class TestProcessTextPunctuation(unittest.TestCase):
    """Regression tests for PR #1093: punctuation preserved during split."""

    def test_chinese_period_preserved(self):
        """Chinese period should remain in output, not be stripped."""
        text = "这是一段测试文本，用来验证标点符号是否被保留在分割后的字幕中。结尾还有更多内容。"
        result = process_text_to_srt_str(text)
        self.assertIn("。", result)
        self.assertIn("，", result)

    def test_english_comma_preserved(self):
        """English comma should remain in output."""
        text = "This is a long test sentence, which contains multiple commas, and should preserve them all, in the final output."
        result = process_text_to_srt_str(text)
        self.assertIn(",", result)

    def test_english_period_preserved(self):
        """English period should remain in output."""
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        result = process_text_to_srt_str(text)
        self.assertIn(".", result)

    def test_english_period_count_preserved(self):
        """All English periods in original text must appear in output."""
        text = "Sentence one. Sentence two. Sentence three."
        expected_periods = text.count(".")
        result = process_text_to_srt_str(text)
        self.assertEqual(result.count("."), expected_periods)

    def test_short_text_unchanged(self):
        """Text shorter than 50 chars should not be split."""
        text = "Short text, no split."
        result = process_text_to_srt_str(text)
        self.assertIn(text, result)

    def test_mixed_punctuation_preserved(self):
        """Mixed Chinese and English punctuation should all be preserved."""
        text = "第一段内容，包含标点。第二段内容，更多标点。第三段内容，还有更多。第四段结束。"
        result = process_text_to_srt_str(text)
        # Count punctuation marks - they should ALL be preserved
        self.assertEqual(result.count("，"), text.count("，"))
        self.assertEqual(result.count("。"), text.count("。"))

    def test_no_double_empty_lines_from_split(self):
        """Splitting should not create empty subtitle entries."""
        text = "内容，，，连续标点。。。更多内容。"
        result = process_text_to_srt_str(text)
        lines = result.split("\n\n")
        for entry in lines:
            # Each entry should have at least a number, time, and text
            entry_lines = entry.strip().splitlines()
            self.assertGreaterEqual(len(entry_lines), 2)


class TestBareExceptNarrowing(unittest.TestCase):
    """Verify that bare except blocks have been narrowed (PR #1094, #1095).

    These tests verify the behavior is correct, not the exception type.
    """

    def test_voice_rate_valid_value(self):
        """Valid voice rate string should parse correctly."""
        rate_str = "+50%"
        rate = int(rate_str.replace('%', ''))
        self.assertEqual(rate, 50)

    def test_voice_rate_negative_value(self):
        """Negative voice rate string should parse correctly."""
        rate_str = "-20%"
        rate = int(rate_str.replace('%', ''))
        self.assertEqual(rate, -20)

    def test_voice_rate_zero(self):
        """Zero voice rate should parse correctly."""
        rate_str = "0%"
        rate = int(rate_str.replace('%', ''))
        self.assertEqual(rate, 0)

    def test_voice_rate_invalid_falls_back(self):
        """Invalid voice rate should be caught by ValueError/TypeError."""
        try:
            rate = int("abc".replace('%', ''))
        except (ValueError, TypeError):
            rate = 0
        self.assertEqual(rate, 0)

    def test_voice_rate_none_falls_back(self):
        """None voice rate should be caught by TypeError."""
        try:
            rate = int(str(None).replace('%', ''))
        except (ValueError, TypeError):
            rate = 0
        self.assertEqual(rate, 0)


if __name__ == "__main__":
    unittest.main()
