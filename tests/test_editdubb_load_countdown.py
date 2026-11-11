import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans.util._srt_parse import ms_to_time_string

# numbers of dubbed lines: load_table() fills the first 200 rows, then the rest
# 500 at a time
LINES = [150, 201, 1300]
LINES_IDS = ["150-lines", "201-lines", "1300-lines"]


class _Signal:
    """A Qt signal: emit() calls a slot once for each time it was connected"""

    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class _Table:
    """Stands in for the panel's QTableWidget. As in Qt, setItem() emits
    itemChanged, and blockSignals(True) keeps the table from emitting it."""

    def __init__(self):
        self.itemChanged = _Signal()
        self.cells = {}
        self.blocked = False

    def blockSignals(self, block):
        was, self.blocked = self.blocked, block
        return was

    def changed(self, item):
        if not self.blocked:
            self.itemChanged.emit(item)

    def setItem(self, row, column, item):
        item.table, item.at = self, (row, column)
        self.cells[row, column] = item
        self.changed(item)

    def item(self, row, column):
        return self.cells.get((row, column))

    def __getattr__(self, name):
        # the layout and style of the table, and its other signals
        return MagicMock()


class _Item:
    """Stands in for QTableWidgetItem. As in Qt, setText() emits the table's
    itemChanged when the text changes."""

    def __init__(self, text=""):
        self._text = text
        self.table = None
        self.at = (-1, -1)

    def text(self):
        return self._text

    def setText(self, text):
        if text != self._text:
            self._text = text
            if self.table is not None:
                self.table.changed(self)

    def row(self):
        return self.at[0]

    def column(self):
        return self.at[1]

    def setFlags(self, flags):
        pass

    def setData(self, role, value):
        pass

    def setTextAlignment(self, alignment):
        pass

    def setForeground(self, brush):
        pass


@pytest.fixture
def editdubb(monkeypatch, tmp_path):
    """The Proofreading and dubbing - Re-dubbing panel (EditDubbingResultDialog),
    with stand-ins for its table cells and buttons, so that no QApplication is
    needed. The callbacks given to QTimer.singleShot() wait in pending, as they
    wait for Qt's event loop after load_table() returns."""
    import PySide6

    if isinstance(PySide6, MagicMock):
        # conftest.py's stand-in for PySide6, when it isn't installed, has no
        # QtMultimedia, and its QDialog is a MagicMock, which can't be a base
        # class: the panel is imported with stand-ins of its own
        widgets = MagicMock()
        widgets.QDialog = type("QDialog", (), {})
        monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", widgets)
        for name in ("PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"):
            monkeypatch.setitem(sys.modules, name, MagicMock())
    from videotrans.component import onlyone_set_editdubb

    # load_table() deletes the files of the last re-dub
    monkeypatch.setattr(
        onlyone_set_editdubb, "REDUBB_QUEUE_FILE", (tmp_path / "queue.json").as_posix()
    )
    monkeypatch.setattr(
        onlyone_set_editdubb, "REDUBB_STATUS_FILE", (tmp_path / "status.txt").as_posix()
    )
    monkeypatch.setattr(onlyone_set_editdubb, "QTableWidgetItem", _Item)
    monkeypatch.setattr(onlyone_set_editdubb, "QPushButton", MagicMock())
    pending = []
    timer = MagicMock()
    timer.singleShot.side_effect = lambda ms, callback: pending.append(callback)
    monkeypatch.setattr(onlyone_set_editdubb, "QTimer", timer)
    return SimpleNamespace(
        cls=onlyone_set_editdubb.EditDubbingResultDialog, pending=pending
    )


@pytest.fixture
def adjusted(monkeypatch, editdubb):
    """Returns the (row, 'start' or 'end', offset in ms) of each _adjust_time() call"""
    calls = []
    adjust_time = editdubb.cls._adjust_time

    def spy(self, row, mode, offset_ms):
        calls.append((row, mode, offset_ms))
        return adjust_time(self, row, mode, offset_ms)

    monkeypatch.setattr(editdubb.cls, "_adjust_time", spy)
    return calls


def _queue(lines):
    """queue_tts.json of a dubbed video: a line every 2 s, 1.5 s long and dubbed
    in 1.2 s"""
    queue = []
    for i in range(lines):
        start = 100 + i * 2000
        queue.append(
            {
                "line": i + 1,
                "start_time": start,
                "end_time": start + 1500,
                "startraw": ms_to_time_string(ms=start),
                "endraw": ms_to_time_string(ms=start + 1500),
                "text": f"Line {i + 1}.",
                "dubbing_s": 1.2,
                "filename": f"{i}.wav",
                "tts_type": 0,
            }
        )
    return queue


def _times(queue):
    return [(it["start_time"], it["end_time"]) for it in queue]


def _open(editdubb, lines):
    """Shows the panel with the given number of dubbed lines: runs load_table(),
    which fills the first rows and starts the countdown"""
    panel = editdubb.cls.__new__(editdubb.cls)
    panel.parent = None
    panel.queue_tts = _queue(lines)
    panel.table = _Table()
    panel.loading_widget = MagicMock()
    panel.loading_label = MagicMock()
    panel.prompt_label = MagicMock()
    panel.stop_button = MagicMock()
    panel.isVisible = lambda: True
    panel._play_with_video = lambda *args: None
    panel.load_table()
    # load_table() shows its errors there
    panel.loading_label.setText.assert_not_called()
    return panel


def _finish_loading(editdubb):
    """Runs what Qt's event loop runs next: _load_remaining() fills the other rows"""
    while editdubb.pending:
        editdubb.pending.pop(0)()


@pytest.mark.parametrize("lines", LINES, ids=LINES_IDS)
def test_countdown_keeps_running_when_the_table_is_filled(editdubb, adjusted, lines):
    panel = _open(editdubb, lines)
    countdown = panel.timer

    _finish_loading(editdubb)

    # every row is filled
    assert panel.table.item(lines - 1, 6).text() == f"Line {lines}."
    # the countdown runs on, and can still be stopped
    countdown.stop.assert_not_called()
    assert panel.timer is countdown
    assert panel.stop_button is not None
    # no time was changed
    assert adjusted == []
    assert _times(panel.queue_tts) == _times(_queue(lines))


@pytest.mark.parametrize(
    "while_loading", [False, True], ids=["after-loading", "while-loading"]
)
@pytest.mark.parametrize("lines", LINES, ids=LINES_IDS)
def test_an_edited_time_is_applied_once(editdubb, adjusted, lines, while_loading):
    panel = _open(editdubb, lines)
    countdown = panel.timer
    if not while_loading:
        _finish_loading(editdubb)

    # line 6 starts at 10.1 s: the user types 10.3 in its start cell
    panel.table.item(5, 3).setText("10.3")
    _finish_loading(editdubb)

    assert adjusted == [(5, "start", 200.0)]
    assert panel.queue_tts[5]["start_time"] == 10300
    assert panel.table.item(5, 3).text() == "10.3"
    # as with the other ways of changing a time, the countdown stops
    countdown.stop.assert_called_once()
    assert panel.timer is None


def test_edits_still_apply_after_a_batch_fails(editdubb, adjusted):
    """A batch that raises while it fills the table must not leave the table's
    signals blocked, or every time the user types afterwards would be ignored"""
    panel = _open(editdubb, 300)
    del panel.queue_tts[250]["startraw"]
    with pytest.raises(KeyError):
        _finish_loading(editdubb)

    assert panel.table.blocked is False
    panel.table.item(5, 3).setText("10.3")

    assert adjusted == [(5, "start", 200.0)]
    assert panel.queue_tts[5]["start_time"] == 10300
