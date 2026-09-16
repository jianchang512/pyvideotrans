from videotrans.util.help_srt import get_subtitle_from_srt


def test_plain_text_becomes_a_single_subtitle():
    result = get_subtitle_from_srt("Hello world\nSecond line", is_file=False)
    assert len(result) == 1
    assert result[0]["text"] == "Hello world\nSecond line"


def test_plain_text_file_becomes_a_single_subtitle(tmp_path):
    txt = tmp_path / "plain.srt"
    txt.write_text("Bonjour", encoding="utf-8")
    result = get_subtitle_from_srt(str(txt), is_file=True)
    assert result[0]["text"] == "Bonjour"
