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
                          filename=config.TEMP_HOME + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.TEMP_HOME + "/test.wav")
            QtWidgets.QMessageBox.information(gptsovitsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(gptsovitsw, config.transobj['anerror'], d)
        gptsovitsw.test.setText('测试api')

    def test():
        url = gptsovitsw.api_url.text()
        config.params["gptsovits_url"] = url
        task = TestTTS(parent=gptsovitsw,
                       text="你好啊我的朋友",
                       role=getrole(),
                       language="zh")
        gptsovitsw.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = gptsovitsw.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 3:
                QtWidgets.QMessageBox.critical(gptsovitsw, config.transobj['anerror'],
                                               "每行都必须以#分割为三部分，格式为   音频名称.wav#音频文字内容#音频语言代码")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(gptsovitsw, config.transobj['anerror'],
                                               "每行都必须以#分割为三部分，格式为  音频名称.wav#音频文字内容#音频语言代码 ,并且第一部分为.wav结尾的音频名称")
                return
            if s[2] not in ['zh', 'ja', 'en']:
                QtWidgets.QMessageBox.critical(gptsovitsw, config.transobj['anerror'],
                                               "每行必须以#分割为三部分，格式为 音频名称.wav#音频文字内容#音频语言代码 ,并且第三部分语言代码只能是 zh或en或ja")
                return
            role = s[0]
        config.params['gptsovits_role'] = tmp
        return role

    def save():
        url = gptsovitsw.api_url.text()
        extra = gptsovitsw.extra.text()
        role = gptsovitsw.role.toPlainText().strip()

        config.params["gptsovits_url"] = url
        config.params["gptsovits_extra"] = extra
        config.params["gptsovits_role"] = role
        config.getset_params(config.params)

        gptsovitsw.close()

    from videotrans.component import GPTSoVITSForm
    gptsovitsw = config.child_forms.get('gptsovitsw')
    if gptsovitsw is not None:
        gptsovitsw.show()
        gptsovitsw.raise_()
        gptsovitsw.activateWindow()
        return
    gptsovitsw = GPTSoVITSForm()
    config.child_forms['gptsovitsw'] = gptsovitsw
    if config.params["gptsovits_url"]:
        gptsovitsw.api_url.setText(config.params["gptsovits_url"])
    if config.params["gptsovits_extra"]:
        gptsovitsw.extra.setText(config.params["gptsovits_extra"])
    if config.params["gptsovits_role"]:
        gptsovitsw.role.setPlainText(config.params["gptsovits_role"])

    gptsovitsw.save.clicked.connect(save)
    gptsovitsw.test.clicked.connect(test)
    gptsovitsw.show()
