from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore

from videotrans import winform
from videotrans.configure import config
from videotrans.configure._app_params import AppParams
from videotrans.configure.config import tr
from videotrans.ui import _bottom_btn
from videotrans.util import help_misc
from videotrans.winform import fn_subtitlescover

# the Batch Subtitle Format Converter keeps the folder chosen in its window here
KEY = "subtitlescover_output_data"
SRT = (
    "1\n00:00:01,000 --> 00:00:03,500\nHello there.\n\n"
    "2\n00:00:04,000 --> 00:00:06,200\nHow are you?\n"
)


class Window(_bottom_btn._Bottom_btn_layout):
    """Stands in for the window of a tool, which adds the row with its output
    folder at its bottom when it is built"""

    output_key = KEY


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
def params(monkeypatch, tmp_path):
    # widgets that need no QApplication
    monkeypatch.setattr(_bottom_btn, "QtWidgets", MagicMock())
    # the folder of a fresh install, which has no output folder yet
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(_bottom_btn, "ROOT_DIR", root.as_posix())
    # params of their own: the windows read the chosen folders from them, and
    # nothing is saved to params.json
    params = AppParams(_json_path=(tmp_path / "params.json").as_posix())
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setattr(_bottom_btn, "params", params)
    monkeypatch.setattr(config, "params", params)
    return params


def _shown_folder():
    """Builds the row as the window does, and returns the folder it shows"""
    win = Window()
    win.get_bottom_btn_layout()
    return win.output_data.setText.call_args.args[0]


def test_default_folder_is_created(params, tmp_path):
    folder = tmp_path / "root" / "output"

    assert _shown_folder() == folder.as_posix()
    assert folder.is_dir()


def test_chosen_folder_is_created_again(params, tmp_path):
    # chosen with "Set output directory" (设置输出目录), and removed afterwards
    folder = tmp_path / "results" / "subtitles"
    params[KEY] = folder.as_posix()

    assert _shown_folder() == folder.as_posix()
    assert folder.is_dir()


def test_window_opens_when_the_folder_cannot_be_created(params, tmp_path):
    # e.g. on a drive that has been removed; here a file is in the way
    file = tmp_path / "results"
    file.write_text("")
    folder = (file / "subtitles").as_posix()
    params[KEY] = folder

    assert _shown_folder() == folder


def test_converter_saves_into_the_default_folder(monkeypatch, params, tmp_path):
    # the window of the Batch Subtitle Format Converter, with the folder that
    # the row shows at its bottom
    win = MagicMock()
    win.output_data.text.return_value = _shown_folder()
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    # openwin() imports them from PySide6.QtCore when it is called
    monkeypatch.setattr(QtCore, "QThread", Thread)
    monkeypatch.setattr(QtCore, "Signal", Signal)
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr(config, "TEMP_DIR", temp.as_posix())
    # instead of a dialog, an error shown by the window fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    fn_subtitlescover.openwin()
    srt = tmp_path / "talk.srt"
    srt.write_text(SRT, encoding="utf-8")
    # the chosen file and target format
    win.subtitlefiles = [srt.as_posix()]
    win.formatlist.currentText.return_value = "txt"

    start = win.startbtn.clicked.connect.call_args.args[0]
    start()

    txt = tmp_path / "root" / "output" / "talk.txt"
    assert txt.read_text(encoding="utf-8") == "Hello there.\nHow are you?"
    win.logs.setText.assert_called_with(tr("quanbuend"))
