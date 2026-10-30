"""
Tests for the start-time check that the selected TTS channel supports the
target language (WinActionCheckMixin.check_tts_lang).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.mainwin import _actions_check
from videotrans.mainwin._actions_check import WinActionCheckMixin


def _combo(text="", index=0):
    return SimpleNamespace(currentText=lambda: text, currentIndex=lambda: index)


def _win(voice_role, target_code, tts_type):
    main = SimpleNamespace(
        voice_role=_combo(voice_role),
        target_language=_combo(target_code),
        tts_type=_combo(index=tts_type),
    )
    return SimpleNamespace(main=main)


@pytest.fixture
def msgbox(monkeypatch):
    """Replace QMessageBox so the test can choose the user's answer."""
    box = MagicMock()
    box.StandardButton.Yes = 1
    box.StandardButton.No = 2
    qtwidgets = MagicMock(QMessageBox=box)
    monkeypatch.setitem(__import__("sys").modules, "PySide6.QtWidgets", qtwidgets)
    # target_language holds a language code here, get_code returns it as is
    monkeypatch.setattr(_actions_check.translator, "get_code", lambda show_text=None: show_text)
    return box


def test_qwen3_local_arabic_is_flagged():
    assert tts.is_allow_lang(langcode="ar", tts_type=tts.QWEN3LOCAL_TTS) is not True


def test_supported_language_does_not_ask(msgbox):
    win = _win("Vivian", "en", tts.QWEN3LOCAL_TTS)
    assert WinActionCheckMixin.check_tts_lang(win) is True
    msgbox.question.assert_not_called()


def test_no_dubbing_does_not_ask(msgbox):
    win = _win("No", "ar", tts.QWEN3LOCAL_TTS)
    assert WinActionCheckMixin.check_tts_lang(win) is True
    msgbox.question.assert_not_called()


def test_unsupported_language_user_cancels(msgbox):
    msgbox.question.return_value = msgbox.StandardButton.No
    win = _win("Vivian", "ar", tts.QWEN3LOCAL_TTS)
    assert WinActionCheckMixin.check_tts_lang(win) is False
    msgbox.question.assert_called_once()


def test_unsupported_language_user_continues(msgbox):
    msgbox.question.return_value = msgbox.StandardButton.Yes
    win = _win("Vivian", "ar", tts.QWEN3LOCAL_TTS)
    assert WinActionCheckMixin.check_tts_lang(win) is True
