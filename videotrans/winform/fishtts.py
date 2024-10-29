from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools


def openwin():
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
                                "filename": config.TEMP_HOME + "/testfishtts.mp3", "tts_type": tts.FISHTTS}],
                    language="zh",
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
        winobj.test.setText('测试api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["fishtts_url"] = url
        task = TestTTS(parent=winobj,
                       text="你好啊我的朋友",
                       role=getrole())
        winobj.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为   音频名称.wav#音频文字内容")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容")
                return
            role = s[0]
        config.params['fishtts_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()

        config.params["fishtts_url"] = url
        config.params["fishtts_role"] = role

        config.getset_params(config.params)
        tools.set_process(text='fishtts', type="refreshtts")
        winobj.close()

    from videotrans.component import FishTTSForm
    winobj = config.child_forms.get('fishttsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = FishTTSForm()
    config.child_forms['fishttsw'] = winobj
    if config.params["fishtts_url"]:
        winobj.api_url.setText(config.params["fishtts_url"])
    if config.params["fishtts_role"]:
        winobj.role.setPlainText(config.params["fishtts_role"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
