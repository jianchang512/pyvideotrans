from unittest.mock import MagicMock

import pytest

from videotrans.component import clip_video

ASS = r"""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.50,Default,Tom,0,0,0,,Hello there.
Dialogue: 0,0:00:04.00,0:00:06.20,Default,Ann,0,0,0,,{\i1}How{\i0} are you?
Dialogue: 0,0:00:07.00,0:00:09.00,Default,Tom,0,0,0,,Fine, thanks.
"""


def _select(monkeypatch, tmp_path, path):
    """Chooses path with "Select Matching Subtitles" in the Trim Video by
    Subtitles window, and returns the window"""
    dialog = MagicMock()
    dialog.getOpenFileName.return_value = (
        path.as_posix(),
        "Subtitle Files (*.srt *.ass *.vtt)",
    )
    monkeypatch.setattr(clip_video, "QFileDialog", dialog)
    monkeypatch.setattr(clip_video, "settings", {})
    temp_root = tmp_path / "tmp"
    temp_root.mkdir()
    monkeypatch.setattr(clip_video, "TEMP_ROOT", temp_root.as_posix(), raising=False)
    # the rows of the subtitle list and their check boxes, so that no
    # QApplication is needed
    for name in ("QListWidgetItem", "QCheckBox", "QSize"):
        monkeypatch.setattr(clip_video, name, MagicMock())
    win = clip_video.CLIP_VIDEO.__new__(clip_video.CLIP_VIDEO)
    for name in (
        "progress_label",
        "subtitle_list",
        "subtitle_label",
        "output_data",
        "select_all_btn",
        "deselect_all_btn",
        "invert_btn",
    ):
        setattr(win, name, MagicMock())
    win.select_subtitle()
    return win


def _subtitles(win):
    # what "Start Trimming" cuts: one clip per row, from start_time to end_time
    return [(it["start_time"], it["end_time"], it["text"]) for it in win.subtitles]


@pytest.mark.parametrize("name", ["talk.ass", "TALK.ASS"])
def test_each_ass_dialogue_is_a_row(monkeypatch, tmp_path, name):
    ass = tmp_path / name
    ass.write_text(ASS, encoding="utf-8")

    win = _select(monkeypatch, tmp_path, ass)

    assert _subtitles(win) == [
        (1000, 3500, "Hello there."),
        (4000, 6200, "How are you?"),
        (7000, 9000, "Fine, thanks."),
    ]
    assert win.subtitle_list.addItem.call_count == 3
    # the clips are still saved in a folder named after the chosen file, and
    # the next dialog opens in its folder
    assert win.subtitle_name == name
    assert win.subtitle_path == ass.as_posix()
    assert clip_video.settings["last_opendir"] == tmp_path.as_posix()


def test_srt_is_read_as_it_is(monkeypatch, tmp_path):
    srt = tmp_path / "talk.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,500\nHello there.\n\n"
        "2\n00:00:04,000 --> 00:00:06,200\nHow are you?\n",
        encoding="utf-8",
    )

    win = _select(monkeypatch, tmp_path, srt)

    assert _subtitles(win) == [
        (1000, 3500, "Hello there."),
        (4000, 6200, "How are you?"),
    ]
    assert win.subtitle_list.addItem.call_count == 2
    # no converted copy is written
    assert list((tmp_path / "tmp").iterdir()) == []
