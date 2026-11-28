import pytest

from videotrans.util.help_srt import get_subtitle_from_srt


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<font color="#ffff00">Hello</font>', "Hello"),
        ("<i>x</i>", "x"),
        ("a < b > c", "a < b > c"),
        ("<3", "<3"),
    ],
)
def test_srt_tags_are_removed_without_removing_non_tag_text(text, expected):
    srt = f"1\n00:00:01,000 --> 00:00:02,000\n{text}\n"
    result = get_subtitle_from_srt(srt, is_file=False)
    assert len(result) == 1
    assert result[0]["text"] == expected
