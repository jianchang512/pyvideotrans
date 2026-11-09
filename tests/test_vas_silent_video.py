import re
import shutil
import stat
import subprocess
from array import array
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


def duration_ms(file):
    """The length of a file in ms, as ffmpeg shows it"""
    info = ffmpeg("-i", file).stderr.decode("utf-8", "replace")
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


RATE = 8000


def sound(file):
    """The sound track of a file, as RATE mono samples a second"""
    pcm = ffmpeg("-i", file, "-ac", "1", "-ar", f"{RATE}", "-f", "s16le", "-")
    return array("h", pcm.stdout)


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
    # Start reads the streams and the length of the video with ffprobe, and the
    # merge reads the length of the audio file: here ffmpeg lists the streams
    # and gives the length of the audio, and the videos below are 3 s long
    monkeypatch.setattr(
        _ffprobe,
        "get_video_info",
        lambda file: {"streams_audio": streams(file).count("Audio")},
    )
    monkeypatch.setattr(_ffprobe, "get_video_duration", lambda file: 3000)
    monkeypatch.setattr(_ffprobe, "get_audio_time", duration_ms)
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


@needs_ffmpeg
@pytest.mark.parametrize(
    "codec, read_only",
    [
        pytest.param("pcm_s16le", False, id="16-bit"),
        # pydub converts 24-bit audio to 32-bit audio when it reads it
        pytest.param("pcm_s24le", False, id="24-bit"),
        # on a read-only share, for example
        pytest.param("pcm_s16le", True, id="read-only"),
    ],
)
def test_a_shorter_wav_is_padded_without_changing_the_file(
    window, tmp_path, request, codec, read_only
):
    # a black 3 s video without audio, and a 1 s tone as the new sound track
    video = tmp_path / "talk.mp4"
    black = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=3"]
    assert ffmpeg(*black, video.as_posix()).returncode == 0
    wav = tmp_path / "voice.wav"
    tone = ["-f", "lavfi", "-i", "sine=duration=1", "-ac", "2", "-ar", "48000"]
    assert ffmpeg(*tone, "-c:a", codec, wav.as_posix()).returncode == 0
    chosen = wav.read_bytes()
    if read_only:
        wav.chmod(stat.S_IREAD)
        # so that pytest can remove it afterwards
        request.addfinalizer(lambda: wav.chmod(stat.S_IREAD | stat.S_IWRITE))
    # the user chose the video and the audio file, no subtitles
    window.ysphb_videoinput.text.return_value = video.as_posix()
    window.ysphb_wavinput.text.return_value = wav.as_posix()
    window.ysphb_srtinput.text.return_value = ""
    window.ysphb_issoft.isChecked.return_value = False
    window.language.currentText.return_value = "English"
    # checked once an audio file is chosen; this video has no sound to keep
    window.ysphb_replace.isChecked.return_value = True
    window.ysphb_maxlen.text.return_value = "16"
    # Truncate, for audio longer than the video
    window.audio_process.currentIndex.return_value = 0
    window.remain_hr.isChecked.return_value = False

    start = window.ysphb_startbtn.clicked.connect.call_args.args[0]
    start()

    # the chosen file is left as it was
    assert wav.read_bytes() == chosen
    # the window shows the merged video
    results = list((tmp_path / "home" / "vas").glob("*.mp4"))
    assert len(results) == 1
    result = results[0].as_posix()
    window.ysphb_out.setText.assert_called_once_with(result)
    assert streams(result) == ["Video", "Audio"]
    # its sound track is 3 s long: the tone, then silence up to the end of the
    # video. AAC blurs the start and the end of the tone, so the checks leave
    # out 0.1 s next to them
    track = sound(result)
    assert len(track) / RATE == pytest.approx(3, abs=0.05)
    assert max(map(abs, track[RATE // 10 : RATE * 9 // 10])) > 1000
    assert max(map(abs, track[RATE * 11 // 10 :])) < 50
