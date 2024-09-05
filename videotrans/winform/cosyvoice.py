from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools
from videotrans import tts


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.role = role

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": self.text, "role": self.role,
                                "filename": config.TEMP_HOME + "/testcosyvoice.mp3", "tts_type": tts.COSYVOICE_TTS}],
                    language="zh",
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(cosyvoicew, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(cosyvoicew, config.transobj['anerror'], d)
        cosyvoicew.test.setText('测试api')

    def test():
        url = cosyvoicew.api_url.text()
        config.params["cosyvoice_url"] = url
        task = TestTTS(parent=cosyvoicew,
                       text="你好啊我的朋友",
                       role="中文女")
        cosyvoicew.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()


    def save():
        url = cosyvoicew.api_url.text()

        role = cosyvoicew.role.toPlainText().strip()

        config.params["cosyvoice_url"] = url

        config.params["cosyvoice_role"] = role
        config.getset_params(config.params)

        cosyvoicew.close()

    from videotrans.component import CosyVoiceForm
    cosyvoicew = config.child_forms.get('cosyvoicew')
    if cosyvoicew is not None:
        cosyvoicew.show()
        cosyvoicew.raise_()
        cosyvoicew.activateWindow()
        return
    cosyvoicew = CosyVoiceForm()
    config.child_forms['cosyvoicew'] = cosyvoicew
    if config.params["cosyvoice_url"]:
        cosyvoicew.api_url.setText(config.params["cosyvoice_url"])
    if config.params["cosyvoice_role"]:
        cosyvoicew.role.setPlainText(config.params["cosyvoice_role"])

    cosyvoicew.save.clicked.connect(save)
    cosyvoicew.test.clicked.connect(test)
    cosyvoicew.show()
