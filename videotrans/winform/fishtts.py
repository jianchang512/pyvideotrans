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
                          filename=config.TEMP_HOME + "/test.wav")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.TEMP_HOME + "/test.wav")
            QtWidgets.QMessageBox.information(fishttsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(fishttsw, config.transobj['anerror'], d)
        fishttsw.test.setText('测试api')

    def test():
        url = fishttsw.api_url.text()
        config.params["fishtts_url"] = url
        task = TestTTS(parent=fishttsw,
                       text="你好啊我的朋友",
                       role=getrole())
        fishttsw.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = fishttsw.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(fishttsw, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为   音频名称.wav#音频文字内容")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(fishttsw, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容")
                return
            role = s[0]
        config.params['fishtts_role'] = tmp
        return role

    def save():
        url = fishttsw.api_url.text()
        role = fishttsw.role.toPlainText().strip()

        config.params["fishtts_url"] = url
        config.params["fishtts_role"] = role

        config.getset_params(config.params)
        fishttsw.close()

    from videotrans.component import FishTTSForm
    fishttsw = config.child_forms.get('fishttsw')
    if fishttsw is not None:
        fishttsw.show()
        fishttsw.raise_()
        fishttsw.activateWindow()
        return
    fishttsw = FishTTSForm()
    config.child_forms['fishttsw'] = fishttsw
    if config.params["fishtts_url"]:
        fishttsw.api_url.setText(config.params["fishtts_url"])
    if config.params["fishtts_role"]:
        fishttsw.role.setPlainText(config.params["fishtts_role"])

    fishttsw.save.clicked.connect(save)
    fishttsw.test.clicked.connect(test)
    fishttsw.show()
