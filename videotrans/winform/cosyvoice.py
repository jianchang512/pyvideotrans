from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.role = role

        def run(self):
            from videotrans.tts.cosyvoice import get_voice
            try:
                get_voice(text=self.text, set_p=False, role=self.role, language='zh',
                          filename=config.TEMP_HOME + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.TEMP_HOME + "/test.wav")
            QtWidgets.QMessageBox.information(cosyvoicew, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(cosyvoicew, config.transobj['anerror'], d)
        cosyvoicew.test.setText('测试api')

    def test():
        url = cosyvoicew.api_url.text()
        config.params["cosyvoice_url"] = url
        task = TestTTS(parent=cosyvoicew,
                       text="你好啊我的朋友",
                       role=getrole())
        cosyvoicew.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = cosyvoicew.role.toPlainText().strip()
        role = "中文女"
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(cosyvoicew, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容,并且第一部分为.wav结尾的音频名称")
                return

            role = s[0]
        config.params['cosyvoice_role'] = tmp
        return role

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
