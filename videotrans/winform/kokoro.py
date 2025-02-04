from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools


def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": "Hello my friend, welcome to China", "role": "af_alloy",
                                "filename": config.TEMP_HOME + "/testclone.mp3", "tts_type": tts.KOKORO_TTS}],
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
        url = winobj.kokoro_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['kokoro_api'] = url
        task = TestTTS(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.kokoro_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["kokoro_api"] = url
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import KokoroForm
    winobj = config.child_forms.get('kokorow')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = KokoroForm()
    config.child_forms['kokorow'] = winobj
    if config.params["kokoro_api"]:
        winobj.kokoro_address.setText(config.params["kokoro_api"])
    winobj.set_kokoro.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
