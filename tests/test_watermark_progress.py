import shutil
import subprocess
import threading
import time
from pathlib import Path
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


class Signal:
    """Stands in for Signal: emit() passes the message to the window's feed()"""

    def __init__(self, *types):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, text):
        for slot in self.slots:
            slot(text)


class StillRunning(Exception):
    """The progress helper of a video waits for more progress after ffmpeg
    has ended"""


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True
    )


def progress(seconds, end=False):
    """The block that ffmpeg adds to its -progress file when it has encoded
    `seconds` of the video"""
    us = seconds * 1_000_000
    return (
        f"frame={seconds * 25}\nfps=25.00\nstream_0_0_q=28.0\n"
        f"bitrate= 600.0kbits/s\ntotal_size={seconds * 75000}\n"
        f"out_time_us={us}\nout_time_ms={us}\nout_time=00:00:{seconds:02}.000000\n"
        f"dup_frames=0\ndrop_frames=0\nspeed=1.00x\n"
        f"progress={'end' if end else 'continue'}\n"
    )


@pytest.fixture
def window(monkeypatch, tmp_path):
    """Stands in for the window of Batch Add Watermarks, with 4 videos of 4 s
    and the image logo.png chosen"""
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
    # the tool reads the length of each video with ffprobe, for its progress
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 4000)
    # the errors the window shows, instead of a dialog
    win.errors = []
    monkeypatch.setattr(help_misc, "show_error", win.errors.append)
    win.videourls = [(tmp_path / f"talk{i}.mp4").as_posix() for i in range(1, 5)]
    win.pngurl.text.return_value = (tmp_path / "logo.png").as_posix()
    win.linex.text.return_value = "10"
    win.liney.text.return_value = "10"
    win.linew.text.return_value = "50x50"
    win.compos.currentIndex.return_value = 0
    return win


@pytest.fixture
def helpers(monkeypatch):
    """The tool starts the progress helper of each video (hebing_pro) in a
    thread. Here that thread doesn't start: the stand-in for ffmpeg runs the
    helper while it encodes the video. Other threads start as usual"""
    started = []
    real_thread = threading.Thread

    class Helper:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            started.append(self)

    def thread(*args, target=None, **kwargs):
        if getattr(target, "__name__", None) == "hebing_pro":
            return Helper(target, kwargs["args"])
        return real_thread(*args, target=target, **kwargs)

    monkeypatch.setattr(threading, "Thread", thread)
    return started


def run_helper(helpers, command, still_running):
    """Runs the progress helper of the video that `command` encodes, until it
    returns. If it waits for more progress after the end of ffmpeg's progress,
    the stand-in for time.sleep raises StillRunning, and the name of the video
    goes into `still_running`"""
    helper = helpers.pop()
    try:
        helper.target(*helper.args)
    except StillRunning:
        still_running.append(Path(command[command.index("-i") + 1]).name)


def click_start(window):
    """Opens the window and clicks Start"""
    fn_watermark.openwin()
    start = window.startbtn.clicked.connect.call_args.args[0]
    start()


def percents(window):
    """The progress the Start button showed, in %"""
    texts = [c.args[0] for c in window.startbtn.setText.call_args_list]
    return [float(text[:-1]) for text in texts if text.endswith("%")]


def test_the_progress_goes_from_0_to_100(window, helpers, monkeypatch):
    still_running = []

    def runffmpeg(command, **kwargs):
        """Stands in for ffmpeg: it encodes the video, of 4 s, in 4 s, and adds
        a block to the -progress file each second. Meanwhile, the progress
        helper of the video reads that file each second"""
        file = Path(command[command.index("-progress") + 1])
        blocks = [progress(s, end=s == 4) for s in (1, 2, 3, 4)]

        def sleep(seconds):
            # while the helper waits a second, ffmpeg adds its next block
            if not blocks:
                raise StillRunning
            with file.open("ab") as f:
                f.write(blocks.pop(0).encode())

        monkeypatch.setattr(time, "sleep", sleep)
        run_helper(helpers, command, still_running)
        return True

    monkeypatch.setattr(_ffmpeg_runner, "runffmpeg", runffmpeg)

    click_start(window)

    assert window.errors == []
    shown = percents(window)
    assert max(shown) == 100
    # 4 videos of 4 s: each second of a video is 1/16 of the work. The helper
    # shows seconds 1 to 3 of each video, and the tool the end of each video
    assert shown == pytest.approx([100 * n / 16 for n in range(1, 17)])
    assert window.startbtn.setText.call_args.args[0] == config.tr("zhixingwc")
    # the helper of each video returns when ffmpeg's progress ends
    assert still_running == []


@needs_ffmpeg
def test_the_helper_returns_when_ffmpeg_has_ended(
    window, helpers, monkeypatch, tmp_path
):
    # two black 2 s videos, and a red 32x32 image
    window.videourls = window.videourls[:2]
    black = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=2"]
    for video in window.videourls:
        assert ffmpeg(*black, video).returncode == 0
    red = ["-f", "lavfi", "-i", "color=c=red:s=32x32", "-frames:v", "1"]
    assert ffmpeg(*red, (tmp_path / "logo.png").as_posix()).returncode == 0
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 2000)
    still_running = []
    encode = _ffmpeg_runner.runffmpeg

    def runffmpeg(command, **kwargs):
        """Runs ffmpeg, then the progress helper of the video, which finds all
        of ffmpeg's progress in the -progress file"""
        encode(command, **kwargs)

        def sleep(seconds):
            # ffmpeg has ended: there is no more progress to wait for
            raise StillRunning

        monkeypatch.setattr(time, "sleep", sleep)
        run_helper(helpers, command, still_running)
        return True

    monkeypatch.setattr(_ffmpeg_runner, "runffmpeg", runffmpeg)

    click_start(window)

    assert window.errors == []
    assert still_running == []
    # the helpers had nothing more to show: the tool shows the end of each video
    assert percents(window) == [50.0, 100.0]
    assert window.startbtn.setText.call_args.args[0] == config.tr("zhixingwc")
    assert sorted(f.name for f in (tmp_path / "out").iterdir()) == [
        "talk1.mp4",
        "talk2.mp4",
    ]
