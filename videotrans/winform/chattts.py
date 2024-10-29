import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools



def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": self.text, "role": "boy1", "filename": config.TEMP_HOME + "/testchattts.mp3",
                                "tts_type": tts.CHATTTS}],
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
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        
        url = winobj.chattts_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url    
        config.params['chattts_api'] = url
        task = TestTTS(parent=winobj,
                       text="你好啊我的朋友"
                       )
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.chattts_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.rstrip('/').replace('/tts', '')
        voice = winobj.chattts_voice.text().strip()
        config.params["chattts_api"] = url
        config.getset_params(config.params)
        config.settings['chattts_voice'] = voice
        with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

        tools.set_process(text='chattts', type="refreshtts")
        winobj.close()

    from videotrans.component import ChatttsForm
    winobj = config.child_forms.get('chatttsw')
    if winobj is not None:
        config.settings = config.parse_init()
        if config.settings["chattts_voice"]:
            winobj.chattts_voice.setText(config.settings["chattts_voice"])
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatttsForm()
    config.child_forms['chatttsw'] = winobj

    if config.params["chattts_api"]:
        winobj.chattts_address.setText(config.params["chattts_api"])
    if config.settings["chattts_voice"]:
        winobj.chattts_voice.setText(config.settings["chattts_voice"])
    winobj.set_chattts.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
