import re
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore

from videotrans import winform
from videotrans.configure import config
from videotrans.util import _ffmpeg_runner, _ffprobe, help_misc
from videotrans.winform import fn_watermark

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)

# the size of the video, and the "Watermark Dimensions (W x H)", "Watermark
# margin (left/right)" and "Watermark margin (top/bottom)" set in the window
VIDEO_W, VIDEO_H = 320, 240
MARK_W, MARK_H = 48, 32
MARGIN_X, MARGIN_Y = 10, 20

# each item of "Watermark Position", in the order of the list, and where the
# top left corner of the watermark should be
POSITIONS = [
    pytest.param(0, (MARGIN_X, MARGIN_Y), id="upper-left"),
    pytest.param(1, (VIDEO_W - MARK_W - MARGIN_X, MARGIN_Y), id="upper-right"),
    pytest.param(
        2,
        (VIDEO_W - MARK_W - MARGIN_X, VIDEO_H - MARK_H - MARGIN_Y),
        id="bottom-right",
    ),
    pytest.param(3, (MARGIN_X, VIDEO_H - MARK_H - MARGIN_Y), id="bottom-left"),
    pytest.param(4, ((VIDEO_W - MARK_W) / 2, (VIDEO_H - MARK_H) / 2), id="center"),
]


class Signal:
    """Stands in for Signal: emit() passes the message to the window's feed()"""

    def __init__(self, *types):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, text):
        for slot in self.slots:
            slot(text)


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True
    )


@pytest.fixture
def window(monkeypatch, tmp_path):
    """Stands in for the window of Batch Add Watermarks, with the video
    talk.mp4 and the image logo.png chosen"""
    win = MagicMock()

    class Thread:
        """Stands in for QThread: start() runs run() at once"""

        def __init__(self, parent=None):
            pass

        def start(self):
            self.run()

    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    # openwin() imports them from PySide6.QtCore when it is called
    monkeypatch.setattr(QtCore, "QThread", Thread)
    monkeypatch.setattr(QtCore, "Signal", Signal)
    out = tmp_path / "out"
    out.mkdir()
    win.output_data.text.return_value = out.as_posix()
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr(config, "TEMP_DIR", temp.as_posix())
    # the tool reads the length of the video with ffprobe, for its progress
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 1000)
    # the errors the window shows, instead of a dialog
    win.errors = []
    monkeypatch.setattr(help_misc, "show_error", win.errors.append)
    win.videourls = [(tmp_path / "talk.mp4").as_posix()]
    win.pngurl.text.return_value = (tmp_path / "logo.png").as_posix()
    win.linex.text.return_value = str(MARGIN_X)
    win.liney.text.return_value = str(MARGIN_Y)
    win.linew.text.return_value = f"{MARK_W}x{MARK_H}"
    return win


def click_start(window, position):
    """Opens the window, chooses the Watermark Position and clicks Start"""
    fn_watermark.openwin()
    window.compos.currentIndex.return_value = position
    start = window.startbtn.clicked.connect.call_args.args[0]
    start()


def overlay_xy(command):
    """Where the overlay filter of the ffmpeg command puts the top left corner
    of the watermark. In its x and y, main_w and main_h (also W and H) are the
    size of the video, overlay_w and overlay_h (also w and h) the size of the
    watermark"""
    graph = command[command.index("-filter_complex") + 1]
    x, y = re.search(r"overlay=([^:]+):([^:]+):", graph).groups()
    size = {
        "main_w": VIDEO_W,
        "W": VIDEO_W,
        "main_h": VIDEO_H,
        "H": VIDEO_H,
        "overlay_w": MARK_W,
        "w": MARK_W,
        "overlay_h": MARK_H,
        "h": MARK_H,
    }
    return tuple(eval(e, {"__builtins__": {}}, size) for e in (x, y))


def red_box(video):
    """The box (left, top, right, bottom) of the red pixels in the first frame
    of the video"""
    frame = ffmpeg(
        "-i", video, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
    ).stdout
    assert len(frame) == VIDEO_W * VIDEO_H * 3
    red = [i for i in range(VIDEO_W * VIDEO_H) if frame[3 * i] > 128]
    if not red:
        return None
    xs = [i % VIDEO_W for i in red]
    ys = [i // VIDEO_W for i in red]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


@pytest.mark.parametrize("position, corner", POSITIONS)
def test_the_overlay_puts_the_watermark_at_the_position(
    window, monkeypatch, position, corner
):
    commands = []
    monkeypatch.setattr(
        _ffmpeg_runner, "runffmpeg", lambda command, **kw: commands.append(command)
    )

    click_start(window, position)

    assert window.errors == []
    assert len(commands) == 1
    assert overlay_xy(commands[0]) == corner


@needs_ffmpeg
@pytest.mark.parametrize("position, corner", POSITIONS)
def test_the_watermark_lands_at_the_position(window, tmp_path, position, corner):
    # a black 320x240 video of 1 s, and a red 32x32 image, scaled to 48x32
    black = ["-f", "lavfi", "-i", f"color=c=black:s={VIDEO_W}x{VIDEO_H}:d=1"]
    assert ffmpeg(*black, (tmp_path / "talk.mp4").as_posix()).returncode == 0
    red = ["-f", "lavfi", "-i", "color=c=red:s=32x32", "-frames:v", "1"]
    assert ffmpeg(*red, (tmp_path / "logo.png").as_posix()).returncode == 0

    click_start(window, position)

    assert window.errors == []
    x, y = corner
    # the video is encoded with loss: an edge can be a pixel off
    box = red_box((tmp_path / "out" / "talk.mp4").as_posix())
    assert box == pytest.approx((x, y, x + MARK_W, y + MARK_H), abs=1)
