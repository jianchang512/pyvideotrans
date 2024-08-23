from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

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
            from videotrans.tts.azuretts import get_voice
            try:
                get_voice(text=self.text, role=self.role, rate="+0%", language=self.language, set_p=False,
                          filename=config.homedir + "/test.mp3")

                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.mp3")
            QtWidgets.QMessageBox.information(config.azurettsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.azurettsw, config.transobj['anerror'], d)
        config.azurettsw.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = config.azurettsw.speech_key.text().strip()
        if not key:
            QtWidgets.QMessageBox.critical(config.azurettsw, config.transobj['anerror'], '填写Azure speech key ')
            return
        region = config.azurettsw.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = config.azurettsw.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region

        task = TestTTS(parent=config.azurettsw,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend',
                       role="zh-CN-YunjianNeural" if config.defaulelang == 'zh' else 'en-US-AvaNeural',
                       language="zh-CN" if config.defaulelang == 'zh' else 'en-US'
                       )
        config.azurettsw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = config.azurettsw.speech_key.text()
        region = config.azurettsw.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = config.azurettsw.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        config.getset_params(config.params)
        config.azurettsw.close()

    from videotrans.component import AzurettsForm
    if config.azurettsw is not None:
        config.azurettsw.show()
        config.azurettsw.raise_()
        config.azurettsw.activateWindow()
        return
    config.azurettsw = AzurettsForm()
    if config.params['azure_speech_region'] and config.params['azure_speech_region'].startswith('http'):
        config.azurettsw.speech_region.setText(config.params['azure_speech_region'])
    else:
        config.azurettsw.azuretts_area.setCurrentText(config.params['azure_speech_region'])
    if config.params['azure_speech_key']:
        config.azurettsw.speech_key.setText(config.params['azure_speech_key'])
    config.azurettsw.save.clicked.connect(save)
    config.azurettsw.test.clicked.connect(test)
    config.azurettsw.show()
