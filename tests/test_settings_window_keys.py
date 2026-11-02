import importlib
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from videotrans.configure._app_params import AppParams
from videotrans.configure._app_settings import AppSettings
from videotrans.configure.config import app_cfg, params, settings

# conftest.py puts a MagicMock in place of PySide6 when it isn't installed,
# and these tests need the real windows
pytestmark = pytest.mark.skipif(
    isinstance(QApplication, MagicMock), reason="needs PySide6"
)

# a widget can't be created without a QApplication
app = QApplication.instance() or QApplication([])

DEFAULTS = AppParams._get_defaults()


@pytest.fixture(autouse=True)
def _params(monkeypatch):
    # Save writes params.json, and update_ui() writes the model list to cfg.json:
    # leave both files as they are
    monkeypatch.setattr(AppParams, "save", lambda self, data=None: None)
    monkeypatch.setattr(AppSettings, "save", lambda self, data=None: None)
    # every key of the three channels starts from its default and gets its value back afterwards
    for key, value in DEFAULTS.items():
        if key.startswith(("openrouter_", "deepseek_", "minimaxi_")):
            monkeypatch.setattr(params, key, value)
    for key in ("openrouter_model", "deepseek_model"):
        monkeypatch.setattr(settings, key, settings[key])
    # MiniMax's Save asks the main window to reload the voices: print it instead
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")


def _open(name):
    # what winform.get_win() does when the window is opened from the menu, without showing it
    win = importlib.import_module(f"videotrans.winform.{name}").openwin()
    win.update_ui()
    return win


def test_openrouter_save_keeps_reasoning_effort():
    win = _open("openrouter")
    win.reasoning_effort.setCurrentText("none")

    win.set.click()

    # the key that the OpenRouter translator reads
    assert params["openrouter_reasoning_effort"] == "none"
    # opened again, get_win() calls update_ui() on the same window
    win.update_ui()
    assert win.reasoning_effort.currentText() == "none"


@pytest.mark.parametrize("effort", ["none", "high"], ids=["default", "saved"])
def test_deepseek_window_shows_and_keeps_reasoning_effort(monkeypatch, effort):
    # "none" is the default, "high" a value saved before
    monkeypatch.setattr(params, "deepseek_reasoning_effort", effort)
    win = _open("deepseek")

    assert win.reasoning_effort.currentText() == effort
    # e.g. Save after entering the API key
    win.deepseek_key.setText("sk-test")
    win.set.click()
    assert params["deepseek_reasoning_effort"] == effort


@pytest.mark.parametrize("max_token", [16384, "32768"], ids=["default", "saved"])
def test_minimax_window_shows_and_keeps_max_token(monkeypatch, max_token):
    # 16384 is the default, "32768" a value saved before
    monkeypatch.setattr(params, "minimaxi_max_token", max_token)
    win = _open("minimaxi")

    assert win.max_token.text() == str(max_token)
    win.save.click()
    assert params["minimaxi_max_token"] == str(max_token)
