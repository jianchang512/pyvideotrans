import re
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore

from videotrans import winform
from videotrans.configure import config
from videotrans.util import _ffprobe, help_misc
from videotrans.winform import fn_vas

SRT = (
    "1\n00:00:00,500 --> 00:00:02,000\nHello there\n\n"
    "2\n00:00:02,000 --> 00:00:02,900\nSecond\n"
)

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


class Thread:
    """Stands in for QThread: start() runs the merge at once"""

    def __init__(self, parent=None):
        pass

    def start(self):
        self.run()


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


def streams(file):
    """The kinds of the streams of a file, as ffmpeg lists them"""
    info = ffmpeg("-i", file).stderr.decode("utf-8", "replace")
    return re.findall(r"Stream #0:\d+.*?: (Video|Audio|Subtitle)", info)


@pytest.fixture
def window(monkeypatch, tmp_path):
    """Stands in for the window, whose widgets hold what the user chose"""
    win = MagicMock()
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    # openwin() imports them from PySide6.QtCore when it is called
    monkeypatch.setattr(QtCore, "QThread", Thread)
    monkeypatch.setattr(QtCore, "Signal", Signal)
    monkeypatch.setattr(config, "HOME_DIR", (tmp_path / "home").as_posix())
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr(config, "TEMP_DIR", temp.as_posix())
    # the software encoder, without probing for hardware encoders
    monkeypatch.setattr(config.app_cfg, "video_codec", "libx264")
    # Start reads the streams and the length of the video with ffprobe: here
    # ffmpeg lists the streams, and the videos below are 3 s long
    monkeypatch.setattr(
        _ffprobe,
        "get_video_info",
        lambda file: {"streams_audio": streams(file).count("Audio")},
    )
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 3000)
    # instead of a dialog, an error shown by the window fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    fn_vas.openwin()
    return win


@needs_ffmpeg
@pytest.mark.parametrize(
    "kinds",
    [
        # a screen recording without a microphone, for example
        pytest.param(["Video"], id="video-without-audio"),
        pytest.param(["Video", "Audio"], id="video-with-audio"),
    ],
)
def test_hard_subtitles_are_burned_into_the_video(window, tmp_path, kinds):
    # a black 3 s video, with a tone as its sound track or without one
    video = tmp_path / "talk.mp4"
    inputs = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=3"]
    if "Audio" in kinds:
        inputs += ["-f", "lavfi", "-i", "sine=duration=3"]
    assert ffmpeg(*inputs, video.as_posix()).returncode == 0
    assert streams(video.as_posix()) == kinds
    srt = tmp_path / "talk.srt"
    srt.write_text(SRT, encoding="utf-8")
    # the user chose the video and the subtitles, no audio, and kept the
    # defaults: hard subtitles, 16 characters per line
    window.ysphb_videoinput.text.return_value = video.as_posix()
    window.ysphb_wavinput.text.return_value = ""
    window.ysphb_srtinput.text.return_value = srt.as_posix()
    window.ysphb_issoft.isChecked.return_value = False
    window.language.currentText.return_value = "English"
    window.ysphb_replace.isChecked.return_value = False
    window.ysphb_maxlen.text.return_value = "16"
    window.audio_process.currentIndex.return_value = 0
    window.remain_hr.isChecked.return_value = False

    start = window.ysphb_startbtn.clicked.connect.call_args.args[0]
    start()

    # the window shows the merged video, which keeps the sound track, if any
    results = list((tmp_path / "home" / "vas").glob("*.mp4"))
    assert len(results) == 1
    result = results[0].as_posix()
    window.ysphb_out.setText.assert_called_once_with(result)
    assert streams(result) == kinds
    # the picture is black, and shows the first subtitle at 1 s
    gray = ["-f", "rawvideo", "-pix_fmt", "gray", "-"]
    frame = ffmpeg("-ss", "1", "-i", result, "-frames:v", "1", *gray).stdout
    assert max(frame) > 0
