import importlib
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def realtime_stt(monkeypatch, tmp_path):
    """The module of the Real-time Speech-to-Text window, with tmp_path/output
    as the output folder of the app. Returns it with the folders that the
    window opened"""
    # the speech recognition and the microphone, which the window imports and
    # these tests don't use
    for name in ("onnxruntime", "sherpa_onnx", "sounddevice"):
        if importlib.util.find_spec(name) is None:
            monkeypatch.setitem(sys.modules, name, MagicMock())
    module = importlib.import_module("videotrans.component.realtime_stt")
    monkeypatch.setattr(module, "HOME_DIR", (tmp_path / "output").as_posix())
    # nothing is opened on the desktop: the folders are recorded instead
    opened = []
    url = SimpleNamespace(fromLocalFile=lambda path: path)
    desktop = SimpleNamespace(openUrl=opened.append)
    monkeypatch.setattr(module, "QUrl", url)
    monkeypatch.setattr(module, "QDesktopServices", desktop)
    return SimpleNamespace(module=module, opened=opened)


def _click(realtime_stt):
    """Clicks "Recordings saved in:" (录音存放到) at the bottom of the window"""
    realtime_stt.module.REALTIME_STT.open_dir()


def test_the_folder_is_created_on_a_fresh_install(realtime_stt, tmp_path):
    # nothing has made the output folder yet: no recording has been made, and
    # no window that creates it has been opened
    folder = tmp_path / "output" / "realtime_stt"

    _click(realtime_stt)

    assert folder.is_dir()
    assert realtime_stt.opened == [folder.as_posix()]


def test_the_folder_is_created_in_the_output_folder(realtime_stt, tmp_path):
    # the output folder exists, for example made by the window of a tool
    folder = tmp_path / "output" / "realtime_stt"
    folder.parent.mkdir()

    _click(realtime_stt)

    assert folder.is_dir()
    assert realtime_stt.opened == [folder.as_posix()]


def test_the_folder_of_the_recordings_is_opened(realtime_stt, tmp_path):
    # the folder where the window saved a recording
    folder = tmp_path / "output" / "realtime_stt"
    folder.mkdir(parents=True)
    wav = folder / "20261112_10-00-00.wav"
    wav.write_bytes(b"")

    _click(realtime_stt)

    assert list(folder.iterdir()) == [wav]
    assert realtime_stt.opened == [folder.as_posix()]
