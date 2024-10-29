from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools


def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, language=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.language = language
            self.role = role

        def run(self):
            try:
                tools.get_clone_role(True)
                if len(config.params["clone_voicelist"]) < 2:
                    raise Exception('没有可供测试的声音')
                tts.run(
                    queue_tts=[{"text": self.text, "role": config.params["clone_voicelist"][1],
                                "filename": config.TEMP_HOME + "/testclone.mp3", "tts_type": tts.CLONE_VOICE_TTS}],
                    language=self.language,
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
        url = winobj.clone_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['clone_api'] = url
        task = TestTTS(parent=winobj,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend'
                       , language="zh-cn" if config.defaulelang == 'zh' else 'en')
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.clone_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["clone_api"] = url
        config.getset_params(config.params)
        tools.set_process(text='clone', type="refreshtts")
        winobj.close()

    from videotrans.component import CloneForm
    winobj = config.child_forms.get('clonew')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = CloneForm()
    config.child_forms['clonew'] = winobj
    if config.params["clone_api"]:
        winobj.clone_address.setText(config.params["clone_api"])
    winobj.set_clone.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
