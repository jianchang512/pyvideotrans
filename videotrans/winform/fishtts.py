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
            from videotrans.tts.fishtts import get_voice
            try:
                get_voice(text=self.text, set_p=False, role=self.role,
                          filename=config.homedir + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.wav")
            QtWidgets.QMessageBox.information(config.fishttsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.fishttsw, config.transobj['anerror'], d)
        config.fishttsw.test.setText('测试api')

    def test():
        url = config.fishttsw.api_url.text()
        config.params["fishtts_url"] = url
        task = TestTTS(parent=config.fishttsw,
                       text="你好啊我的朋友",
                       role=getrole())
        config.fishttsw.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = config.fishttsw.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(config.fishttsw, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为   音频名称.wav#音频文字内容")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(config.fishttsw, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容")
                return
            role = s[0]
        config.params['fishtts_role'] = tmp
        return role

    def save():
        url = config.fishttsw.api_url.text()
        role = config.fishttsw.role.toPlainText().strip()

        config.params["fishtts_url"] = url
        config.params["fishtts_role"] = role

        config.getset_params(config.params)
        config.fishttsw.close()

    from videotrans.component import FishTTSForm
    if config.fishttsw is not None:
        config.fishttsw.show()
        config.fishttsw.raise_()
        config.fishttsw.activateWindow()
        return
    config.fishttsw = FishTTSForm()
    if config.params["fishtts_url"]:
        config.fishttsw.api_url.setText(config.params["fishtts_url"])
    if config.params["fishtts_role"]:
        config.fishttsw.role.setPlainText(config.params["fishtts_role"])

    config.fishttsw.save.clicked.connect(save)
    config.fishttsw.test.clicked.connect(test)
    config.fishttsw.show()
