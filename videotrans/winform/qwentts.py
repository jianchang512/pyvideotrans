import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools
import time
# set chatgpt
def openwin():
    class TestQwentts(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None,role=""):
            super().__init__(parent=parent)
            self.text = text
            self.role=role

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": self.text, "role": self.role,
                                "filename": config.TEMP_HOME + f"/testqwentts-{time.time()}.mp3", "tts_type": tts.QWEN_TTS}],
                    language="zh-CN",
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test_qwentts.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.qwentts_key.text().strip()
        if not key:
            QtWidgets.QMessageBox.warning(winobj, "Error", "API Key is empty")
            return

        model = winobj.qwentts_model.currentText()
        config.params["qwentts_key"] = key
        config.params["qwentts_model"] = model
        config.getset_params(config.params)
        task = TestQwentts(parent=winobj, text="你好啊我的朋友",role=winobj.edit_roles.toPlainText().strip().split(',')[0])
        winobj.test_qwentts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        winobj.test_qwentts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_qwentts():
        key = winobj.qwentts_key.text()


        model = winobj.qwentts_model.currentText()

        config.params["qwentts_key"] = key
        config.params["qwentts_model"] = model
        config.getset_params(config.params)
        tools.set_process(text='qwentts', type="refreshtts")
        winobj.close()


    def setedit_roles():
        t = winobj.edit_roles.toPlainText().strip().replace('，', ',').rstrip(',')
        config.params['qwentts_role'] = t
        config.getset_params(config.params)    

    def update_ui():
        winobj.qwentts_model.clear()
        winobj.qwentts_model.addItems(['qwen-tts-latest'])
        winobj.edit_roles.setPlainText(config.params['qwentts_role'])

        if config.params["qwentts_key"]:
            winobj.qwentts_key.setText(config.params["qwentts_key"])
        if config.params["qwentts_model"]:
            winobj.qwentts_model.setCurrentText(config.params["qwentts_model"])

    from videotrans.component import QwenTTSForm
    winobj = config.child_forms.get('qwenttsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = QwenTTSForm()
    config.child_forms['qwenttsw'] = winobj
    update_ui()

    winobj.set_qwentts.clicked.connect(save_qwentts)
    winobj.test_qwentts.clicked.connect(test)
    winobj.edit_roles.textChanged.connect(setedit_roles)
    winobj.show()
