from unittest.mock import MagicMock

import pytest

from videotrans.component import clip_video

# the .vtt that Speech-To-Text and the Batch Subtitle Format Converter save:
# they convert an .srt with ffmpeg, which writes the times of the first hour
# without hours
VTT = """WEBVTT

00:01.000 --> 00:03.500
Hello there.

00:04.000 --> 00:06.200
How are you?

00:07.000 --> 00:09.000
Fine, thanks.
"""

# {h} is "" for times without hours, "00:" for times with hours
ZH_VTT = """WEBVTT

{h}00:01.000 --> {h}00:03.500
大家好。

{h}00:04.000 --> {h}00:06.200
你好，最近怎么样？

{h}00:07.000 --> {h}00:09.000
很好，谢谢。
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


@pytest.mark.parametrize("name", ["talk.vtt", "TALK.VTT"])
def test_vtt_times_without_hours(monkeypatch, tmp_path, name):
    vtt = tmp_path / name
    vtt.write_text(VTT, encoding="utf-8")

    win = _select(monkeypatch, tmp_path, vtt)

    assert _subtitles(win) == [
        (1000, 3500, "Hello there."),
        (4000, 6200, "How are you?"),
        (7000, 9000, "Fine, thanks."),
    ]
    assert win.subtitle_list.addItem.call_count == 3
    # the clips are still saved in a folder named after the chosen file, and
    # the next dialog opens in its folder
    assert win.subtitle_name == name
    assert win.subtitle_path == vtt.as_posix()
    assert clip_video.settings["last_opendir"] == tmp_path.as_posix()
    # no converted copy is written
    assert list((tmp_path / "tmp").iterdir()) == []


def test_vtt_past_the_first_hour(monkeypatch, tmp_path):
    # ffmpeg writes the hours only of the times that have them
    vtt = tmp_path / "long.vtt"
    vtt.write_text(
        "WEBVTT\n\n"
        "00:01.000 --> 00:03.500\nHello there.\n\n"
        "59:58.000 --> 01:00:01.000\nAcross the hour.\n\n"
        "01:00:04.000 --> 01:00:06.200\nPast the first hour.\n",
        encoding="utf-8",
    )

    win = _select(monkeypatch, tmp_path, vtt)

    assert _subtitles(win) == [
        (1000, 3500, "Hello there."),
        (3598000, 3601000, "Across the hour."),
        (3604000, 3606200, "Past the first hour."),
    ]


@pytest.mark.parametrize("hours", ["", "00:"], ids=["without-hours", "with-hours"])
def test_gbk_vtt(monkeypatch, tmp_path, hours):
    # saved as GBK (ANSI on Simplified Chinese Windows)
    vtt = tmp_path / "talk.vtt"
    vtt.write_bytes(ZH_VTT.format(h=hours).encode("gbk"))

    win = _select(monkeypatch, tmp_path, vtt)

    assert _subtitles(win) == [
        (1000, 3500, "大家好。"),
        (4000, 6200, "你好，最近怎么样？"),
        (7000, 9000, "很好，谢谢。"),
    ]
