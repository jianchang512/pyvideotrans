from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import Qt

from videotrans.configure import config
from videotrans.util import tools


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, language=None, rate="+0%", role=None):
            super().__init__(parent=parent)
            self.text = text
            self.language = language
            self.rate = rate
            self.role = role

        def run(self):

            from videotrans.tts.ttsapi import get_voice
            try:

                get_voice(text=self.text, language=self.language, rate=self.rate, role=self.role, set_p=False,
                          filename=config.TEMP_HOME + "/test.mp3")

                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.TEMP_HOME + "/test.mp3")
            QtWidgets.QMessageBox.information(ttsapiw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(ttsapiw, config.transobj['anerror'], d)
        ttsapiw.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = ttsapiw.api_url.text()
        extra = ttsapiw.extra.text()
        role = ttsapiw.voice_role.text().strip()

        config.params["ttsapi_url"] = url
        config.params["ttsapi_extra"] = extra
        config.params["ttsapi_voice_role"] = role

        task = TestTTS(parent=ttsapiw,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend',
                       role=ttsapiw.voice_role.text().strip().split(',')[0],
                       language="zh-cn" if config.defaulelang == 'zh' else 'en')
        ttsapiw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = ttsapiw.api_url.text()
        extra = ttsapiw.extra.text()
        role = ttsapiw.voice_role.text().strip()

        config.params["ttsapi_url"] = url
        config.params["ttsapi_extra"] = extra
        config.params["ttsapi_voice_role"] = role
        config.getset_params(config.params)
        ttsapiw.close()

    from videotrans.component import TtsapiForm
    ttsapiw = config.child_forms.get('ttsapiw')
    if ttsapiw is not None:
        ttsapiw.show()
        ttsapiw.raise_()
        ttsapiw.activateWindow()
        return
    ttsapiw = TtsapiForm()
    config.child_forms['ttsapiw'] = ttsapiw
    if config.params["ttsapi_url"]:
        ttsapiw.api_url.setText(config.params["ttsapi_url"])
    if config.params["ttsapi_voice_role"]:
        ttsapiw.voice_role.setText(config.params["ttsapi_voice_role"])
    if config.params["ttsapi_extra"]:
        ttsapiw.extra.setText(config.params["ttsapi_extra"])

    ttsapiw.save.clicked.connect(save)
    ttsapiw.test.clicked.connect(test)
    ttsapiw.otherlink.clicked.connect(lambda: tools.open_url('https://github.com/kungful/openvoice-api'))
    ttsapiw.otherlink.setCursor(Qt.PointingHandCursor)
    ttsapiw.show()
