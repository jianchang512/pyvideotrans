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
            from videotrans.tts.clone import get_voice
            try:
                tools.get_clone_role(True)
                if len(config.params["clone_voicelist"]) < 2:
                    raise Exception('没有可供测试的声音')
                get_voice(text=self.text, language=self.language, role=config.params["clone_voicelist"][1],
                          set_p=False,
                          filename=config.homedir + "/test.mp3")

                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.mp3")
            QtWidgets.QMessageBox.information(config.clonew, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.clonew, config.transobj['anerror'], d)
        config.clonew.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        if not config.clonew.clone_address.text().strip():
            QtWidgets.QMessageBox.critical(config.clonew, config.transobj['anerror'], '必须填写http地址')
            return
        config.params['clone_api'] = config.clonew.clone_address.text().strip()
        task = TestTTS(parent=config.clonew,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend'
                       , language="zh-cn" if config.defaulelang == 'zh' else 'en')
        config.clonew.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = config.clonew.clone_address.text().strip()
        if key:
            key = key.rstrip('/')
            key = 'http://' + key.replace('http://', '')
        config.params["clone_api"] = key
        config.getset_params(config.params)
        config.clonew.close()

    from videotrans.component import CloneForm
    if config.clonew is not None:
        config.clonew.show()
        config.clonew.raise_()
        config.clonew.activateWindow()
        return
    config.clonew = CloneForm()
    if config.params["clone_api"]:
        config.clonew.clone_address.setText(config.params["clone_api"])
    config.clonew.set_clone.clicked.connect(save)
    config.clonew.test.clicked.connect(test)
    config.clonew.show()
