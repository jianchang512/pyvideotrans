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


def duration_ms(file):
    """The length of a file in ms, as ffmpeg shows it"""
    info = ffmpeg("-i", file).stderr.decode("utf-8", "replace")
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


@pytest.fixture
def window(monkeypatch, tmp_path):
    """Stands in for the window, with a video and an audio file chosen"""
    win = MagicMock()
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
    # Start reads the streams and the length of the video with ffprobe, and the
    # merge reads the length of the audio file: here ffmpeg lists the streams
    # and gives the length of the audio, and the video below is 3 s long
    monkeypatch.setattr(
        _ffprobe,
        "get_video_info",
        lambda file: {"streams_audio": streams(file).count("Audio")},
    )
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 3000)
    monkeypatch.setattr(_ffprobe, "get_audio_time", duration_ms)
    # the errors the window shows, instead of a dialog
    win.errors = []
    monkeypatch.setattr(help_misc, "show_error", win.errors.append)
    fn_vas.openwin()

    # a black 3 s video without audio, and a 1 s tone as its sound track
    video = tmp_path / "talk.mp4"
    black = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=3"]
    assert ffmpeg(*black, video.as_posix()).returncode == 0
    wav = tmp_path / "voice.wav"
    tone = ["-f", "lavfi", "-i", "sine=duration=1", "-ac", "2", "-ar", "48000"]
    assert ffmpeg(*tone, wav.as_posix()).returncode == 0
    # no subtitles: the merged video is made in the temp folder, then copied
    # into the output folder
    win.ysphb_videoinput.text.return_value = video.as_posix()
    win.ysphb_wavinput.text.return_value = wav.as_posix()
    win.ysphb_srtinput.text.return_value = ""
    win.ysphb_issoft.isChecked.return_value = False
    win.language.currentText.return_value = "English"
    # checked once an audio file is chosen; this video has no sound to keep
    win.ysphb_replace.isChecked.return_value = True
    win.ysphb_maxlen.text.return_value = "16"
    win.audio_process.currentIndex.return_value = 0
    win.remain_hr.isChecked.return_value = False
    return win


def button_texts(window):
    return [c.args[0] for c in window.ysphb_startbtn.setText.call_args_list]


@needs_ffmpeg
def test_complete_is_shown_once_the_video_is_saved(window, tmp_path):
    out = tmp_path / "out"
    # the videos in the output folder, and their sizes, when the button shows
    # "Execution Complete"
    shown = []

    def set_text(text):
        if text == config.tr("zhixingwc"):
            shown.append({f.name: f.stat().st_size for f in out.glob("*.mp4")})

    window.ysphb_startbtn.setText.side_effect = set_text

    start = window.ysphb_startbtn.clicked.connect.call_args.args[0]
    start()

    assert window.errors == []
    results = list(out.glob("*.mp4"))
    assert len(results) == 1
    assert streams(results[0].as_posix()) == ["Video", "Audio"]
    # the merged video was already saved, whole, when the merge was shown as
    # complete
    assert shown == [{results[0].name: results[0].stat().st_size}]


@needs_ffmpeg
def test_an_error_is_shown_when_the_video_cannot_be_saved(window, tmp_path):
    # the output folder shown at the bottom of the window doesn't exist any
    # more, as when it has been deleted or renamed since the window was opened
    gone = tmp_path / "gone"
    window.output_data.text.return_value = gone.as_posix()

    start = window.ysphb_startbtn.clicked.connect.call_args.args[0]
    start()

    assert not gone.exists()
    # the error of the copy is shown, and the button can start a merge again
    assert len(window.errors) == 1
    assert "talk-" in window.errors[0]
    texts = button_texts(window)
    assert config.tr("zhixingwc") not in texts
    assert texts[-1] == config.tr("start operate")
    window.ysphb_startbtn.setDisabled.assert_called_with(False)
