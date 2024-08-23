from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, language=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.language = language
            self.role = role

        def run(self):
            from videotrans.tts.gptsovits import get_voice
            try:
                get_voice(text=self.text, language=self.language, set_p=False, role=self.role,
                          filename=config.homedir + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.wav")
            QtWidgets.QMessageBox.information(config.gptsovitsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.gptsovitsw, config.transobj['anerror'], d)
        config.gptsovitsw.test.setText('测试api')

    def test():
        url = config.gptsovitsw.api_url.text()
        config.params["gptsovits_url"] = url
        task = TestTTS(parent=config.gptsovitsw,
                       text="你好啊我的朋友",
                       role=getrole(),
                       language="zh")
        config.gptsovitsw.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = config.gptsovitsw.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 3:
                QtWidgets.QMessageBox.critical(config.gptsovitsw, config.transobj['anerror'],
                                               "每行都必须以#分割为三部分，格式为   音频名称.wav#音频文字内容#音频语言代码")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(config.gptsovitsw, config.transobj['anerror'],
                                               "每行都必须以#分割为三部分，格式为  音频名称.wav#音频文字内容#音频语言代码 ,并且第一部分为.wav结尾的音频名称")
                return
            if s[2] not in ['zh', 'ja', 'en']:
                QtWidgets.QMessageBox.critical(config.gptsovitsw, config.transobj['anerror'],
                                               "每行必须以#分割为三部分，格式为 音频名称.wav#音频文字内容#音频语言代码 ,并且第三部分语言代码只能是 zh或en或ja")
                return
            role = s[0]
        config.params['gptsovits_role'] = tmp
        return role

    def save():
        url = config.gptsovitsw.api_url.text()
        extra = config.gptsovitsw.extra.text()
        role = config.gptsovitsw.role.toPlainText().strip()

        config.params["gptsovits_url"] = url
        config.params["gptsovits_extra"] = extra
        config.params["gptsovits_role"] = role
        config.getset_params(config.params)

        config.gptsovitsw.close()

    from videotrans.component import GPTSoVITSForm
    if config.gptsovitsw is not None:
        config.gptsovitsw.show()
        config.gptsovitsw.raise_()
        config.gptsovitsw.activateWindow()
        return
    config.gptsovitsw = GPTSoVITSForm()
    if config.params["gptsovits_url"]:
        config.gptsovitsw.api_url.setText(config.params["gptsovits_url"])
    if config.params["gptsovits_extra"]:
        config.gptsovitsw.extra.setText(config.params["gptsovits_extra"])
    if config.params["gptsovits_role"]:
        config.gptsovitsw.role.setPlainText(config.params["gptsovits_role"])

    config.gptsovitsw.save.clicked.connect(save)
    config.gptsovitsw.test.clicked.connect(test)
    config.gptsovitsw.show()
