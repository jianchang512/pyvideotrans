from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from videotrans.component.component import DropButton, PeiyinDropButton, Textedit

# conftest.py puts a MagicMock in place of PySide6 when it isn't installed,
# and these tests need Qt's own QUrl and QMimeData
pytestmark = pytest.mark.skipif(isinstance(QUrl, MagicMock), reason="needs PySide6")

# a widget can't be created without a QApplication
app = QApplication.instance() or QApplication([])

IDS = ["DropButton", "PeiyinDropButton"]


def _drop(widget, urls=(), text=None):
    # a drop that carries the URLs of files, as from a file manager,
    # or only text, as from a text editor
    mime = QMimeData()
    if urls:
        mime.setUrls(urls)
    if text is not None:
        mime.setText(text)
    event = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    widget.dropEvent(event)


@pytest.mark.parametrize(
    ("button_cls", "paths", "text"),
    [
        (
            DropButton,
            [
                "/Users/michael/Downloads/zzp.mp3",
                "/home/ann/Videos/100%.mp4",
                "/home/ann/Videos/Talk [a1B2c3D4e5F].mp4",
                "//nas/share/a#1.mp4",
            ],
            "4 files \nzzp.mp3\n100%.mp4\nTalk [a1B2c3D4e5F].mp4\na#1.mp4",
        ),
        (
            PeiyinDropButton,
            [
                "/Users/michael/Downloads/zzp.srt",
                "/home/ann/Subs/100%.srt",
                "/home/ann/Subs/Talk [a1B2c3D4e5F].srt",
                "//nas/share/a#1.txt",
            ],
            "4 files \nzzp.srt\n100%.srt\nTalk [a1B2c3D4e5F].srt\na#1.txt",
        ),
    ],
    ids=IDS,
)
def test_dropped_files_keep_their_paths(button_cls, paths, text):
    button = button_cls("Select files")

    _drop(button, [QUrl.fromLocalFile(p) for p in paths])

    assert button.filelist == paths
    # the names are listed as when the files are chosen in the file dialog
    assert button.text() == text


@pytest.mark.parametrize(
    ("button_cls", "ext"), [(DropButton, "mp4"), (PeiyinDropButton, "srt")], ids=IDS
)
def test_links_that_are_not_local_files_are_skipped(button_cls, ext):
    button = button_cls("Select files")

    _drop(
        button,
        [
            QUrl(f"https://example.com/talk.{ext}"),
            QUrl.fromLocalFile(f"/home/ann/talk.{ext}"),
        ],
    )

    assert button.filelist == [f"/home/ann/talk.{ext}"]


@pytest.mark.parametrize(
    ("button_cls", "ext"), [(DropButton, "mp4"), (PeiyinDropButton, "srt")], ids=IDS
)
def test_paths_dropped_as_text_are_read_as_before(button_cls, ext):
    button = button_cls("Select files")

    # a drop without URLs, e.g. paths dragged from a text editor
    _drop(button, text=f"C:/Videos/a.{ext}\nfile:///C:/Videos/b.{ext}")

    assert button.filelist == [f"C:/Videos/a.{ext}", f"C:/Videos/b.{ext}"]


@pytest.mark.parametrize("dropped_as", ["url", "text"])
def test_text_box_shows_the_dropped_file(tmp_path, dropped_as):
    # the text box of the Text-to-Speech window
    path = tmp_path / "Talk [a1B2c3D4e5F] 100%.srt"
    path.write_text("Hello\n", encoding="utf-8")
    box = Textedit()

    if dropped_as == "url":
        _drop(box, [QUrl.fromLocalFile(str(path))])
    else:
        _drop(box, text=str(path))

    assert box.toPlainText() == "Hello"
