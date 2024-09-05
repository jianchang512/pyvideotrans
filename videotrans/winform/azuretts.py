from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, role=None, language=None):
            super().__init__(parent=parent)
            self.text = text
            self.role = role
            self.language = language

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": self.text, "role": self.role, "filename": config.TEMP_HOME + "/testaiazure.mp3", "tts_type": tts.AI302_TTS}],
                    language=self.language,
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(azurettsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(azurettsw, config.transobj['anerror'], d)
        azurettsw.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = azurettsw.speech_key.text().strip()
        if not key:
            QtWidgets.QMessageBox.critical(azurettsw, config.transobj['anerror'], '填写Azure speech key ')
            return
        region = azurettsw.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = azurettsw.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region

        task = TestTTS(parent=azurettsw,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend',
                       role="zh-CN-YunjianNeural" if config.defaulelang == 'zh' else 'en-US-AvaNeural',
                       language="zh-CN" if config.defaulelang == 'zh' else 'en-US'
                       )
        azurettsw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = azurettsw.speech_key.text()
        region = azurettsw.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = azurettsw.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        config.getset_params(config.params)
        azurettsw.close()

    from videotrans.component import AzurettsForm
    azurettsw = config.child_forms.get('azurettsw')
    if azurettsw is not None:
        azurettsw.show()
        azurettsw.raise_()
        azurettsw.activateWindow()
        return
    azurettsw = AzurettsForm()
    config.child_forms['azurettsw'] = azurettsw
    if config.params['azure_speech_region'] and config.params['azure_speech_region'].startswith('http'):
        azurettsw.speech_region.setText(config.params['azure_speech_region'])
    else:
        azurettsw.azuretts_area.setCurrentText(config.params['azure_speech_region'])
    if config.params['azure_speech_key']:
        azurettsw.speech_key.setText(config.params['azure_speech_key'])
    azurettsw.save.clicked.connect(save)
    azurettsw.test.clicked.connect(test)
    azurettsw.show()
