import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore

from videotrans import winform
from videotrans.configure import config
from videotrans.util import _ffprobe, help_misc
from videotrans.winform import fn_videoandaudio, fn_watermark

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


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True
    )


def streams(file):
    """The kinds of the streams of a file, as ffmpeg lists them"""
    info = ffmpeg("-i", file).stderr.decode("utf-8", "replace")
    return re.findall(r"Stream #0:\d+.*?: (Video|Audio|Subtitle)", info)


def duration_ms(file):
    """The length of a file in ms, as ffmpeg shows it"""
    info = ffmpeg("-i", file).stderr.decode("utf-8", "replace")
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


@pytest.fixture(params=["videoandaudio", "watermark"])
def window(request, monkeypatch, tmp_path):
    """Stands in for the window of Merge Video & Audio or of Batch Add
    Watermarks, with the video talk.mp4 chosen"""
    # the app's working folder: the test puts it back afterwards
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.chdir(app)
    win = MagicMock()
    # the exceptions that end the tool's thread
    win.raised = []

    class Thread:
        """Stands in for QThread: start() runs run() at once. As in a thread,
        an exception that ends run() doesn't reach the code that started it"""

        def __init__(self, parent=None):
            pass

        def start(self):
            try:
                self.run()
            except Exception as e:
                win.raised.append(e)

    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    # openwin() imports them from PySide6.QtCore when it is called
    monkeypatch.setattr(QtCore, "QThread", Thread)
    monkeypatch.setattr(QtCore, "Signal", Signal)
    # the output folder shown at the bottom of the window: the window creates it
    out = tmp_path / "out"
    out.mkdir()
    win.output_data.text.return_value = out.as_posix()
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr(config, "TEMP_DIR", temp.as_posix())
    # the tools read the lengths of the video and of the audio with ffprobe:
    # here ffmpeg gives them
    monkeypatch.setattr(_ffprobe, "get_video_duration", duration_ms)
    monkeypatch.setattr(_ffprobe, "get_audio_time", duration_ms)
    # the errors the window shows, instead of a dialog
    win.errors = []
    monkeypatch.setattr(help_misc, "show_error", win.errors.append)

    # a black 2 s video without audio
    media = tmp_path / "media"
    media.mkdir()
    video = media / "talk.mp4"
    black = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=2"]
    assert ffmpeg(*black, video.as_posix()).returncode == 0
    if request.param == "videoandaudio":
        fn_videoandaudio.openwin()
        # a 1 s tone with the name of the video, in the same folder
        tone = ["-f", "lavfi", "-i", "sine=duration=1"]
        assert ffmpeg(*tone, (media / "talk.wav").as_posix()).returncode == 0
        win.folder.text.return_value = media.as_posix()
        win.remain.isChecked.return_value = False
        # Truncate, for audio longer than the video
        win.audio_process.currentIndex.return_value = 0
    else:
        fn_watermark.openwin()
        # a red 32x32 image, in the top left corner
        logo = tmp_path / "logo.png"
        red = ["-f", "lavfi", "-i", "color=c=red:s=32x32", "-frames:v", "1"]
        assert ffmpeg(*red, logo.as_posix()).returncode == 0
        win.videourls = [video.as_posix()]
        win.pngurl.text.return_value = logo.as_posix()
        win.linex.text.return_value = "10"
        win.liney.text.return_value = "10"
        win.linew.text.return_value = "32x32"
        win.compos.currentIndex.return_value = 0
    return win


def button_texts(window):
    return [c.args[0] for c in window.startbtn.setText.call_args_list]


@needs_ffmpeg
def test_the_working_folder_is_kept(window, tmp_path):
    start = window.startbtn.clicked.connect.call_args.args[0]
    start()

    assert window.raised == []
    assert window.errors == []
    assert config.tr("zhixingwc") in button_texts(window)
    results = list((tmp_path / "out").iterdir())
    assert [f.name for f in results] == ["talk.mp4"]
    assert "Video" in streams(results[0].as_posix())
    # the app's working folder is still the same, not the output folder
    assert Path.cwd() == tmp_path / "app"


@needs_ffmpeg
def test_an_error_is_shown_when_the_output_folder_is_gone(window, tmp_path):
    # the output folder shown at the bottom of the window doesn't exist any
    # more, as when it has been deleted or renamed since the window was opened
    gone = tmp_path / "gone"
    window.output_data.text.return_value = gone.as_posix()

    start = window.startbtn.clicked.connect.call_args.args[0]
    start()

    # the error is shown, and the button can start the tool again
    assert len(window.errors) == 1
    assert "talk.mp4" in window.errors[0]
    assert button_texts(window)[-1] == config.tr("start operate")
    window.startbtn.setDisabled.assert_called_with(False)
    assert window.raised == []
    assert not gone.exists()
    assert Path.cwd() == tmp_path / "app"
