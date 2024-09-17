from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config


def openwin():
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
                    queue_tts=[{"text": self.text, "role": self.role, "filename": config.TEMP_HOME + "/testaiazure.mp3",
                                "tts_type": tts.AZURE_TTS}],
                    language=self.language,
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.speech_key.text().strip()
        if not key:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], '填写Azure speech key ')
            return
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region

        task = TestTTS(parent=winobj,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend',
                       role="zh-CN-YunjianNeural" if config.defaulelang == 'zh' else 'en-US-AvaNeural',
                       language="zh-CN" if config.defaulelang == 'zh' else 'en-US'
                       )
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.speech_key.text()
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import AzurettsForm
    winobj = config.child_forms.get('azurettsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AzurettsForm()
    config.child_forms['azurettsw'] = winobj
    if config.params['azure_speech_region'] and config.params['azure_speech_region'].startswith('http'):
        winobj.speech_region.setText(config.params['azure_speech_region'])
    else:
        winobj.azuretts_area.setCurrentText(config.params['azure_speech_region'])
    if config.params['azure_speech_key']:
        winobj.speech_key.setText(config.params['azure_speech_key'])
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
