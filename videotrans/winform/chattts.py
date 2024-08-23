import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            from videotrans.tts.chattts import get_voice
            try:
                get_voice(text=self.text, role="boy1", set_p=False, filename=config.homedir + "/test.mp3")

                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.mp3")
            QtWidgets.QMessageBox.information(config.chatttsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.chatttsw, config.transobj['anerror'], d)
        config.chatttsw.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        if not config.chatttsw.chattts_address.text().strip():
            QtWidgets.QMessageBox.critical(config.chatttsw, config.transobj['anerror'], '必须填写http地址')
            return
        apiurl = config.chatttsw.chattts_address.text().strip()
        if not apiurl:
            return QtWidgets.QMessageBox.critical(config.llmw, config.transobj['anerror'],
                                                  '必须填写api地址' if config.defaulelang == 'zh' else 'Please input ChatTTS API url')

        config.params['chattts_api'] = apiurl
        task = TestTTS(parent=config.chatttsw,
                       text="你好啊我的朋友" if config.defaulelang == 'zh' else 'hello,my friend'
                       )
        config.chatttsw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = config.chatttsw.chattts_address.text().strip()
        voice = config.chatttsw.chattts_voice.text().strip()
        key = key.rstrip('/')
        key = 'http://' + key.replace('http://', '').replace('/tts', '')
        config.params["chattts_api"] = key
        config.getset_params(config.params)
        config.settings['chattts_voice'] = voice
        json.dump(config.settings, builtin_open(config.rootdir + "/videotrans/cfg.json", 'w', encoding='utf-8'),
                  ensure_ascii=False)

        config.chatttsw.close()

    from videotrans.component import ChatttsForm
    if config.chatttsw is not None:
        config.chatttsw.show()
        config.chatttsw.raise_()
        config.chatttsw.activateWindow()
        return
    config.chatttsw = ChatttsForm()
    if config.params["chattts_api"]:
        config.chatttsw.chattts_address.setText(config.params["chattts_api"])
    if config.settings["chattts_voice"]:
        config.chatttsw.chattts_voice.setText(config.settings["chattts_voice"])
    config.chatttsw.set_chattts.clicked.connect(save)
    config.chatttsw.test.clicked.connect(test)
    config.chatttsw.show()
