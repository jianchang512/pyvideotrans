import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans.configure.config import app_cfg
from videotrans.util._srt_parse import get_subtitle_from_srt

# the time and text of each line of the subtitles the panel opens
LINES = [
    ("00:00:01,000 --> 00:00:03,500", "Jhon said helo."),
    ("00:00:04,000 --> 00:00:06,200", "Where is Jhon?"),
    ("00:00:07,000 --> 00:00:09,000", "Fine, thanks."),
    ("00:00:10,000 --> 00:00:11,000", "Bye, Jhon."),
    ("00:00:12,000 --> 00:00:14,000", "See you, Jhon."),
]

# the panels of single-video translation that have Replace: module, class and
# the subtitle file they save
PANELS = {
    # Edit transcribed subtitles here to improve translation accuracy
    "recogn": ("onlyone_set_recogn", "EditRecognResultDialog", "source_sub"),
    # Secondary STT: Edit Subtitles
    "recogn2": ("onlyone_set_recogn2", "EditRecognResultDialog2", "source_sub"),
    # Edit Subtitles & Assign Voice Roles
    "role": ("onlyone_set_role", "SpeakerAssignmentDialog", "target_sub"),
}

# the columns of the cells of a row that save_and_close() reads
COLUMNS = {
    "recogn": {"start": 2, "end": 3, "text": 5},
    "recogn2": {"start": 2, "end": 3, "text": 5},
    "role": {"spk": 3, "start": 5, "end": 6, "text": 8},
}


class _Item:
    """A cell of the panel's table. Its text is what the user typed last, as
    QTableWidgetItem.text() returns once an edit is committed."""

    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text


class _Table:
    """The panel's table, with the cells of the rows shown so far"""

    def __init__(self):
        self.cells = {}

    def item(self, row, column):
        return self.cells.get((row, column))

    def setUpdatesEnabled(self, enable):
        pass


class _Panel:
    """A panel that has loaded the subtitles in srt as load_table() does, and
    has shown the first `shown` of them in its table"""

    def __init__(self, name, srt, shown):
        module, cls, sub = PANELS[name]
        module = importlib.import_module(f"videotrans.component.{module}")
        self.cls = getattr(module, cls)
        self.srt = srt
        self.text_column = COLUMNS[name]["text"]
        self.table = _Table()
        self.display_data = []
        for row, it in enumerate(get_subtitle_from_srt(srt)):
            self.display_data.append(
                {
                    "line": it["line"],
                    "text": it["text"],
                    "start_time": it["start_time"],
                    "end_time": it["end_time"],
                    "spk": "",
                    "role": "",
                }
            )
            if row >= shown:
                continue
            cells = {
                "spk": "",
                "start": str(it["start_time"] / 1000.0),
                "end": str(it["end_time"] / 1000.0),
                "text": it["text"],
            }
            for key, column in COLUMNS[name].items():
                self.table.cells[row, column] = _Item(cells[key])
        self.dialog = SimpleNamespace(
            display_data=self.display_data,
            table=self.table,
            speakers={},
            save_button=MagicMock(),
            stop_countdown=lambda: None,
            _release_media=lambda: None,
            accept=lambda: None,
            **{sub: srt.as_posix()},
        )

    def edit(self, row, text):
        """The user types text in the text cell of row"""
        self.table.item(row, self.text_column).setText(text)

    def replace(self, search, replace):
        """The user types search and replace in the boxes above the table and
        clicks Replace"""
        self.dialog.search_input = SimpleNamespace(text=lambda: search)
        self.dialog.replace_input = SimpleNamespace(text=lambda: replace)
        self.cls.replace_text(self.dialog)

    def shown_texts(self):
        return [
            self.table.item(row, self.text_column).text()
            for row in range(len(self.display_data))
        ]

    def save(self):
        """The user clicks Save Changes & Proceed, and gets the texts of the
        saved subtitles"""
        self.cls.save_and_close(self.dialog)
        return [it["text"] for it in get_subtitle_from_srt(self.srt)]


@pytest.fixture(params=list(PANELS))
def open_panel(request, monkeypatch, tmp_path):
    import PySide6

    if isinstance(PySide6, MagicMock):
        # conftest.py's stand-in for PySide6, when it isn't installed, has no
        # QtMultimedia, and its QDialog is a MagicMock, which can't be a base
        # class: the panels are imported with stand-ins of their own
        widgets = MagicMock()
        widgets.QDialog = type("QDialog", (), {})
        monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", widgets)
        for name in ("PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"):
            monkeypatch.setitem(sys.modules, name, MagicMock())
    # save_and_close() of Edit Subtitles & Assign Voice Roles sets the voice of
    # each line here
    monkeypatch.setattr(app_cfg, "line_roles", {})
    srt = tmp_path / "talk.srt"
    srt.write_text(
        "\n".join(f"{i}\n{t}\n{text}\n" for i, (t, text) in enumerate(LINES, 1)),
        encoding="utf-8",
    )

    def open_panel(shown=len(LINES)):
        return _Panel(request.param, srt, shown)

    return open_panel


def test_replace_keeps_the_edits_made_in_the_table(open_panel):
    panel = open_panel()
    # a typo corrected, the name taken out of a line and added to another
    panel.edit(0, "Jhon said hello.")
    panel.edit(1, "Where is he?")
    panel.edit(2, "Fine, thanks, Jhon.")
    # a line deleted, as the panels say: by clearing its text
    panel.edit(3, "")

    panel.replace("Jhon", "John")

    assert panel.shown_texts() == [
        "John said hello.",
        "Where is he?",
        "Fine, thanks, John.",
        "",
        "See you, John.",
    ]
    assert panel.save() == [
        "John said hello.",
        "Where is he?",
        "Fine, thanks, John.",
        "See you, John.",
    ]


def test_replace_reaches_the_rows_not_shown_yet(open_panel):
    # load_table() leaves the rows to timers that add them to the table 50 at a
    # time, after it returns: here only the first row is in the table yet
    panel = open_panel(shown=1)

    panel.replace("Jhon", "John")

    assert panel.table.item(0, panel.text_column).text() == "John said helo."
    # the other rows are shown with their text in display_data
    assert [it["text"] for it in panel.display_data] == [
        "John said helo.",
        "Where is John?",
        "Fine, thanks.",
        "Bye, John.",
        "See you, John.",
    ]
