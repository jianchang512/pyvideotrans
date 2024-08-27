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
                          filename=config.homedir + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.wav")
            QtWidgets.QMessageBox.information(config.cosyvoicew, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.cosyvoicew, config.transobj['anerror'], d)
        config.cosyvoicew.test.setText('测试api')

    def test():
        url = config.cosyvoicew.api_url.text()
        config.params["cosyvoice_url"] = url
        task = TestTTS(parent=config.cosyvoicew,
                       text="你好啊我的朋友",
                       role=getrole())
        config.cosyvoicew.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = config.cosyvoicew.role.toPlainText().strip()
        role = "中文女"
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(config.cosyvoicew, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容,并且第一部分为.wav结尾的音频名称")
                return

            role = s[0]
        config.params['cosyvoice_role'] = tmp
        return role

    def save():
        url = config.cosyvoicew.api_url.text()

        role = config.cosyvoicew.role.toPlainText().strip()

        config.params["cosyvoice_url"] = url

        config.params["cosyvoice_role"] = role
        config.getset_params(config.params)

        config.cosyvoicew.close()

    from videotrans.component import CosyVoiceForm
    if config.cosyvoicew is not None:
        config.cosyvoicew.show()
        config.cosyvoicew.raise_()
        config.cosyvoicew.activateWindow()
        return
    config.cosyvoicew = CosyVoiceForm()
    if config.params["cosyvoice_url"]:
        config.cosyvoicew.api_url.setText(config.params["cosyvoice_url"])
    if config.params["cosyvoice_role"]:
        config.cosyvoicew.role.setPlainText(config.params["cosyvoice_role"])

    config.cosyvoicew.save.clicked.connect(save)
    config.cosyvoicew.test.clicked.connect(test)
    config.cosyvoicew.show()
