import inspect
import pytest
from pathlib import Path
import tempfile


class TestHelpSrtImports:
    """All names from the original help_srt.py must be importable."""

    def test_process_text_to_srt_str(self):
        from videotrans.util.help_srt import process_text_to_srt_str
        assert callable(process_text_to_srt_str)

    def test_is_srt_string(self):
        from videotrans.util.help_srt import is_srt_string
        assert callable(is_srt_string)

    def test_cleartext(self):
        from videotrans.util.help_srt import cleartext
        assert callable(cleartext)

    def test_delete_punc(self):
        from videotrans.util.help_srt import delete_punc
        assert callable(delete_punc)

    def test_ms_to_time_string(self):
        from videotrans.util.help_srt import ms_to_time_string
        assert callable(ms_to_time_string)

    def test_format_time(self):
        from videotrans.util.help_srt import format_time
        assert callable(format_time)

    def test_srt_str_to_listdict(self):
        from videotrans.util.help_srt import srt_str_to_listdict
        assert callable(srt_str_to_listdict)

    def test_get_subtitle_from_srt(self):
        from videotrans.util.help_srt import get_subtitle_from_srt
        assert callable(get_subtitle_from_srt)

    def test_get_srt_from_list(self):
        from videotrans.util.help_srt import get_srt_from_list
        assert callable(get_srt_from_list)

    def test_set_ass_font(self):
        from videotrans.util.help_srt import set_ass_font
        assert callable(set_ass_font)

    def test_simple_wrap(self):
        from videotrans.util.help_srt import simple_wrap
        assert callable(simple_wrap)

    def test_all_11_names_importable(self):
        from videotrans.util import help_srt
        expected = [
            'process_text_to_srt_str', 'is_srt_string', 'cleartext', 'delete_punc',
            'ms_to_time_string', 'format_time', 'srt_str_to_listdict',
            'get_subtitle_from_srt', 'get_srt_from_list',
            'set_ass_font', 'simple_wrap',
        ]
        for name in expected:
            assert hasattr(help_srt, name), f"Missing: {name}"


class TestIsSrtString:
    def test_valid_srt(self):
        from videotrans.util.help_srt import is_srt_string
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello world\n"
        assert is_srt_string(srt) is True

    def test_empty_string(self):
        from videotrans.util.help_srt import is_srt_string
        assert is_srt_string("") is False

    def test_too_few_lines(self):
        from videotrans.util.help_srt import is_srt_string
        assert is_srt_string("line1\nline2") is False

    def test_plain_text(self):
        from videotrans.util.help_srt import is_srt_string
        assert is_srt_string("Just some text without srt format") is False


class TestMsToTimeString:
    def test_zero(self):
        from videotrans.util.help_srt import ms_to_time_string
        result = ms_to_time_string(ms=0)
        assert result == "00:00:00,000"

    def test_one_hour(self):
        from videotrans.util.help_srt import ms_to_time_string
        result = ms_to_time_string(ms=3600000)
        assert result == "01:00:00,000"

    def test_with_seconds(self):
        from videotrans.util.help_srt import ms_to_time_string
        result = ms_to_time_string(seconds=65)
        assert result == "00:01:05,000"

    def test_custom_separator(self):
        from videotrans.util.help_srt import ms_to_time_string
        result = ms_to_time_string(ms=1500, sepflag='.')
        assert result == "00:00:01.500"


class TestFormatTime:
    def test_empty(self):
        from videotrans.util.help_srt import format_time
        assert format_time("") == "00:00:00,000"

    def test_normal(self):
        from videotrans.util.help_srt import format_time
        result = format_time("01:02:03,456")
        assert result == "01:02:03,456"

    def test_missing_hours(self):
        from videotrans.util.help_srt import format_time
        result = format_time("02:03,456")
        assert result == "00:02:03,456"


class TestCleartext:
    def test_removes_special_chars(self):
        from videotrans.util.help_srt import cleartext
        result = cleartext("Hello &#39; world &quot; test \u200b here")
        assert "&#39;" not in result
        assert "&quot;" not in result

    def test_collapses_punctuation(self):
        from videotrans.util.help_srt import cleartext
        result = cleartext("Hello,,,  world")
        assert "Hello," in result
        assert ",,," not in result


class TestDeletePunc:
    def test_removes_punctuation(self):
        from videotrans.util.help_srt import delete_punc
        result = delete_punc("Hello, world! How are you?")
        assert "," not in result
        assert "!" not in result
        assert "?" not in result
        assert "Hello" in result
        assert "world" in result


class TestSrtStrToListdict:
    def test_valid_srt(self):
        from videotrans.util.help_srt import srt_str_to_listdict
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n2\n00:00:04,000 --> 00:00:06,000\nWorld"
        result = srt_str_to_listdict(srt)
        assert len(result) == 2
        assert result[0]['text'] == "Hello"
        assert result[1]['text'] == "World"
        assert result[0]['start_time'] == 1000
        assert result[0]['end_time'] == 3000

    def test_empty(self):
        from videotrans.util.help_srt import srt_str_to_listdict
        result = srt_str_to_listdict("")
        assert len(result) == 0


class TestProcessTextToSrtStr:
    def test_already_srt(self):
        from videotrans.util.help_srt import process_text_to_srt_str
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello"
        result = process_text_to_srt_str(srt)
        assert result == srt

    def test_plain_text(self):
        from videotrans.util.help_srt import process_text_to_srt_str
        result = process_text_to_srt_str("Hello world")
        assert "00:00:00" in result
        assert "Hello" in result
        assert "world" in result


class TestSimpleWrap:
    def test_short_text(self):
        from videotrans.util.help_srt import simple_wrap
        result = simple_wrap("Hi", maxlen=15)
        assert result == "Hi"

    def test_chinese_no_spaces(self):
        from videotrans.util.help_srt import simple_wrap
        result = simple_wrap("这是一个很长的中文句子需要被断行处理", maxlen=10, language="zh")
        assert "\n" in result
        for line in result.split("\n"):
            assert len(line) <= 12

    def test_english_with_spaces(self):
        from videotrans.util.help_srt import simple_wrap
        result = simple_wrap("This is a fairly long English sentence that needs wrapping", maxlen=20, language="en")
        assert "\n" in result


class TestGetSubtitleFromSrt:
    def test_from_string(self):
        from videotrans.util.help_srt import get_subtitle_from_srt
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n2\n00:00:04,000 --> 00:00:06,000\nWorld"
        result = get_subtitle_from_srt(srt, is_file=False)
        assert len(result) == 2
        assert result[0]['text'] == "Hello"

    def test_from_file(self, tmp_path):
        from videotrans.util.help_srt import get_subtitle_from_srt
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nHello", encoding='utf-8')
        result = get_subtitle_from_srt(str(srt_file), is_file=True)
        assert len(result) == 1
        assert result[0]['text'] == "Hello"


class TestGetSrtFromList:
    def test_roundtrip(self):
        from videotrans.util.help_srt import srt_str_to_listdict, get_srt_from_list
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n2\n00:00:04,000 --> 00:00:06,000\nWorld"
        items = srt_str_to_listdict(srt)
        result = get_srt_from_list(items)
        assert "Hello" in result
        assert "World" in result
        assert "-->" in result
