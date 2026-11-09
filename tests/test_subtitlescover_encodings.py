import codecs
import shutil
from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore

from videotrans import winform
from videotrans.configure import config
from videotrans.configure._app_params import AppParams
from videotrans.configure.config import tr
from videotrans.util import help_misc
from videotrans.winform import fn_subtitlescover

SRT = (
    "1\r\n00:00:01,000 --> 00:00:03,500\r\nHello there, friend.\r\n\r\n"
    "2\r\n00:00:04,000 --> 00:00:06,200\r\n你好，世界\r\n"
)
ASS = (
    "[Script Info]\r\nScriptType: v4.00+\r\n\r\n"
    "[V4+ Styles]\r\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\r\n"
    "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\r\n\r\n"
    "[Events]\r\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\r\n"
    "Dialogue: 0,0:00:01.00,0:00:03.50,Default,,0,0,0,,Hello there, friend.\r\n"
    "Dialogue: 0,0:00:04.00,0:00:06.20,Default,,0,0,0,,你好，世界\r\n"
)
# the texts of the two subtitles of both files
LINES = ["Hello there, friend.", "你好，世界"]

# the file chosen in the window and the target format. ffmpeg converts the
# file, and for TXT converts an .ass file to SRT first; TXT from an .srt file
# is read without ffmpeg, with get_subtitle_from_srt(), and a file of the
# target format is meant to be copied
CONVERSIONS = [
    pytest.param("talk.srt", SRT, "ass", id="srt-to-ass"),
    pytest.param("talk.srt", SRT, "vtt", id="srt-to-vtt"),
    pytest.param("talk.srt", SRT, "txt", id="srt-to-txt"),
    pytest.param("talk.ass", ASS, "srt", id="ass-to-srt"),
    pytest.param("talk.ass", ASS, "vtt", id="ass-to-vtt"),
    pytest.param("talk.ass", ASS, "txt", id="ass-to-txt"),
]
# the file saved as UTF-8 with and without a BOM, as GBK ("ANSI" in Notepad on
# Simplified Chinese Windows) and as UTF-16 with a BOM ("Unicode" in Notepad)
ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "utf-16-le", "utf-16-be"]
# the utf-16-le and utf-16-be codecs write no BOM
BOMS = {"utf-16-le": codecs.BOM_UTF16_LE, "utf-16-be": codecs.BOM_UTF16_BE}

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


class Thread:
    """Stands in for QThread: start() runs the conversion at once"""

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
    # params of its own: openwin() reads the last target format from them, and
    # Start keeps the chosen one there without saving it to params.json
    params = AppParams(_json_path=(tmp_path / "params.json").as_posix())
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setattr(config, "params", params)
    # instead of a dialog, an error shown by the window fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    fn_subtitlescover.openwin()
    return win


@needs_ffmpeg
@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("name, text, target", CONVERSIONS)
def test_converted_file_has_every_subtitle(
    window, tmp_path, name, text, target, encoding
):
    file = tmp_path / "subs" / name
    file.parent.mkdir()
    data = BOMS.get(encoding, b"") + text.encode(encoding)
    file.write_bytes(data)
    # the chosen file and target format
    window.subtitlefiles = [file.as_posix()]
    window.formatlist.currentText.return_value = target

    start = window.startbtn.clicked.connect.call_args.args[0]
    start()

    # the result has the name of the chosen file, and is saved as UTF-8
    result = tmp_path / "home" / "subtitlescover" / f"talk.{target}"
    converted = result.read_text(encoding="utf-8")
    assert [line in converted for line in LINES] == [True, True]
    # the window reports that every file has been converted
    window.logs.setText.assert_called_with(tr("quanbuend"))
    # the chosen file is left as it is
    assert file.read_bytes() == data


@needs_ffmpeg
def test_file_neither_utf8_nor_gbk_does_not_stop_the_batch(window, tmp_path):
    # a Big5 file can't be read as GBK either: it goes to ffmpeg as it is, as
    # before, and the files after it are still converted
    with pytest.raises(UnicodeDecodeError):
        SRT.encode("big5").decode("gbk")
    subs = tmp_path / "subs"
    subs.mkdir()
    (subs / "one.srt").write_bytes(SRT.encode("utf-8"))
    (subs / "two.srt").write_bytes(SRT.encode("big5"))
    (subs / "three.ass").write_bytes(ASS.encode("utf-8"))
    window.subtitlefiles = [
        (subs / name).as_posix() for name in ("one.srt", "two.srt", "three.ass")
    ]
    window.formatlist.currentText.return_value = "vtt"

    start = window.startbtn.clicked.connect.call_args.args[0]
    start()

    results = tmp_path / "home" / "subtitlescover"
    for name in ("one", "three"):
        converted = (results / f"{name}.vtt").read_text(encoding="utf-8")
        assert [line in converted for line in LINES] == [True, True]
    # ffmpeg keeps the plain-ASCII subtitle of the Big5 file, as before
    assert LINES[0] in (results / "two.vtt").read_text(encoding="utf-8")
    window.logs.setText.assert_called_with(tr("quanbuend"))
