import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util.help_srt import get_subtitle_from_srt

# the voice chosen in the main window
EMMA = "en-US-EmmaNeural"
# the voice of each speaker
VOICES = {"spk0": "en-US-AvaNeural", "spk1": "en-US-AndrewNeural"}
# (time, spoken text, translation, speaker) of each line of a dialogue
DIALOGUE = [
    ("00:00:01,000 --> 00:00:02,500", "你去哪儿了？", "Where were you?", "spk0"),
    ("00:00:03,000 --> 00:00:03,600", "嗯……", "Um...", "spk1"),
    ("00:00:04,000 --> 00:00:05,500", "在车站。", "At the station.", "spk1"),
    ("00:00:06,000 --> 00:00:07,000", "一整晚？", "All night?", "spk0"),
    ("00:00:07,500 --> 00:00:08,500", "一整晚。", "All night.", "spk1"),
]


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    # the voices of the lines, which the panel sets
    monkeypatch.setattr(app_cfg, "line_roles", {})
    # the cache that _tts() shares between tasks
    cache = tmp_path / "dubbing_cache"
    cache.mkdir()
    monkeypatch.setattr(_stage_dubbing, "DUBBING_CACHE", cache.as_posix())


@pytest.fixture
def role_dialog(monkeypatch):
    """SpeakerAssignmentDialog, the Edit Subtitles & Assign Voice Roles panel"""
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
    from videotrans.component.onlyone_set_role import SpeakerAssignmentDialog

    return SpeakerAssignmentDialog


@pytest.fixture
def dubbed(monkeypatch):
    """Stands in for the TTS channel and returns the (text, voice) of each line it got"""
    lines = []

    def run_tts(*, queue_tts, **kwargs):
        lines.extend((it["text"], it["role"]) for it in queue_tts)

    monkeypatch.setattr(_stage_dubbing, "run_tts", run_tts)
    return lines


def _srt(texts):
    return "\n".join(
        f"{i}\n{line[0]}\n{text}\n"
        for i, (line, text) in enumerate(zip(DIALOGUE, texts), 1)
    )


def _task(tmp_path):
    """A video translation task whose subtitles are recognized and translated"""
    trk = TransCreate(
        cfg=TaskCfgVTT(
            name=(tmp_path / "talk.mp4").as_posix(),
            noextname="talk",
            uuid="talk-uuid",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "tmp").as_posix(),
            source_language_code="zh-cn",
            target_language_code="en",
            voice_role=EMMA,
            tts_type=tts.EDGE_TTS,
        )
    )
    Path(trk.cfg.target_dir).mkdir(parents=True)
    Path(trk.cfg.cache_folder).mkdir(parents=True)
    source = _srt([it[1] for it in DIALOGUE])
    Path(trk.cfg.source_sub).write_text(source, encoding="utf-8")
    target = _srt([it[2] for it in DIALOGUE])
    Path(trk.cfg.target_sub).write_text(target, encoding="utf-8")
    return trk


class _Cell:
    """A cell of the panel's table"""

    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


def _save(role_dialog, target_sub, by_speaker, cleared):
    """Assigns the voices in the panel, per line or per speaker, clears the text of
    the rows in cleared, and clicks "Save Changes & Proceed"."""
    display_data = []
    cells = {}
    for row, it in enumerate(get_subtitle_from_srt(target_sub)):
        # with speaker diarization, the speaker of the line
        spk = DIALOGUE[row][3] if by_speaker else ""
        # "Assign Voice to Selected Subtitles" sets the role of the ticked rows
        role = "" if by_speaker else VOICES[DIALOGUE[row][3]]
        # what save_and_close() reads of the rows that load_table() keeps
        display_data.append(
            {"line": it["line"], "spk": spk, "text": it["text"], "role": role}
        )
        # and of the table: speaker, start and end in seconds, text
        cells[row, 3] = _Cell(spk)
        cells[row, 5] = _Cell(str(it["start_time"] / 1000.0))
        cells[row, 6] = _Cell(str(it["end_time"] / 1000.0))
        cells[row, 8] = _Cell("" if row in cleared else it["text"])
    panel = SimpleNamespace(
        display_data=display_data,
        table=SimpleNamespace(item=lambda row, col: cells.get((row, col))),
        # "Assign Voice Roles to Speakers" sets the voice of each speaker
        speakers=dict(VOICES) if by_speaker else {},
        target_sub=target_sub,
        save_button=MagicMock(),
        stop_countdown=lambda: None,
        _release_media=lambda: None,
        accept=lambda: None,
    )
    role_dialog.save_and_close(panel)


@pytest.mark.parametrize(
    "by_speaker", [False, True], ids=["voice-per-line", "voice-per-speaker"]
)
@pytest.mark.parametrize(
    "cleared",
    [set(), {1}, {0, 2}],
    ids=["no-line-deleted", "line-2-deleted", "lines-1-and-3-deleted"],
)
def test_each_line_is_dubbed_with_its_voice(
    tmp_path, role_dialog, dubbed, by_speaker, cleared
):
    trk = _task(tmp_path)
    # the panel says to delete a line by clearing its text
    _save(role_dialog, trk.cfg.target_sub, by_speaker, cleared)

    trk.dubbing()

    kept = [it for row, it in enumerate(DIALOGUE) if row not in cleared]
    assert dubbed == [(it[2], VOICES[it[3]]) for it in kept]
