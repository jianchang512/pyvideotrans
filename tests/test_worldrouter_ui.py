"""Exercise the real Qt dialog; no API credentials or network are required."""
import os
from unittest.mock import Mock

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6.QtTest')

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QLineEdit

from videotrans.configure.config import params, settings
from videotrans.configure.constants import WORLDROUTER_MODELS
from videotrans.util import TestSrtTrans as test_worker
from videotrans.util import help_misc
from videotrans.winform.worldrouter import openwin


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(app, monkeypatch):
    monkeypatch.setattr(params, 'worldrouter_key', '')
    monkeypatch.setattr(params, 'worldrouter_model', WORLDROUTER_MODELS.split(',')[0])
    monkeypatch.setattr(params, 'worldrouter_max_token', 16384)
    monkeypatch.setattr(settings, 'worldrouter_model', WORLDROUTER_MODELS)
    monkeypatch.setattr(params, 'save', Mock())
    monkeypatch.setattr(settings, 'save', Mock())
    monkeypatch.setattr(help_misc, 'show_error', Mock())
    workers = []

    class FakeWorker(QObject):
        uito = Signal(str)
        finished = Signal()

        def __init__(self, *, parent, translator_type):
            super().__init__(parent)
            self.translator_type = translator_type
            self.started = False
            workers.append(self)

        def start(self):
            self.started = True

    # Patch before openwin captures the worker class in its button callbacks.
    monkeypatch.setattr(test_worker, 'TestSrtTrans', FakeWorker)
    win = openwin()
    win.test_workers = workers
    yield win
    win.close()
    win.deleteLater()
    app.processEvents()


def test_key_is_masked_and_defaults_load(dialog):
    assert dialog.worldrouter_key.echoMode() == QLineEdit.Password
    assert dialog.worldrouter_model.currentText() == 'deepseek-v4-flash'
    assert dialog.max_token.text() == '16384'


def test_save_and_reopen_custom_model(dialog):
    dialog.worldrouter_key.setText(' test-key ')
    dialog.edit_allmodels.setPlainText(WORLDROUTER_MODELS + ',custom-model')
    dialog.worldrouter_model.setCurrentText('custom-model')
    dialog.max_token.setText('4096')
    dialog.set.click()
    params.save.assert_called_once()
    assert params.get('worldrouter_key') == 'test-key'
    dialog.update_ui()
    assert dialog.worldrouter_model.currentText() == 'custom-model'
    assert dialog.max_token.text() == '4096'


@pytest.mark.parametrize('missing', ['key', 'model'])
def test_missing_config_does_not_save_or_start(dialog, missing):
    dialog.worldrouter_key.setText('test-key' if missing != 'key' else ' ')
    if missing == 'model':
        dialog.worldrouter_model.clear()
    dialog.test.click()
    help_misc.show_error.assert_called_once()
    params.save.assert_not_called()
    assert dialog.test.isEnabled()


@pytest.mark.parametrize('value', ['', '0', '-1', '1048577', 'abc'])
def test_invalid_token_limit_does_not_save_or_start(dialog, value):
    dialog.worldrouter_key.setText('test-key')
    dialog.max_token.setText(value)
    dialog.test.click()
    help_misc.show_error.assert_called_once()
    params.save.assert_not_called()
    assert dialog.test_workers == []


def test_previously_saved_custom_model_is_preserved(dialog, monkeypatch):
    monkeypatch.setattr(params, 'worldrouter_model', 'previous-custom-model')
    dialog.update_ui()
    assert dialog.worldrouter_model.currentText() == 'previous-custom-model'
    assert 'previous-custom-model' in dialog.edit_allmodels.toPlainText().split(',')
    settings.save.assert_not_called()


def test_custom_model_list_is_saved_and_reopen_does_not_write(dialog):
    dialog.edit_allmodels.setPlainText('deepseek-v4-flash，custom-model')
    assert settings.get('worldrouter_model') == 'deepseek-v4-flash,custom-model'
    settings.save.assert_called_once()
    dialog.update_ui()
    settings.save.assert_called_once()


def test_test_button_uses_worldrouter_and_recovers_when_finished(dialog):
    from videotrans.translator import WORLDROUTER_INDEX
    workers = dialog.test_workers
    dialog.worldrouter_key.setText('test-key')
    dialog.test.click()
    assert workers[0].started
    assert workers[0].translator_type == WORLDROUTER_INDEX
    assert not dialog.test.isEnabled()
    workers[0].finished.emit()
    assert dialog.test.isEnabled()
