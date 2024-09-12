import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config


# set chatgpt
def openwin():
    class TestOpenaitts(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            try:
                tts.run(
                    queue_tts=[{"text": self.text, "role": "alloy",
                                "filename": config.TEMP_HOME + "/testopenaitts", "tts_type": tts.OPENAI_TTS}],
                    language="zh-CN",
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_openaitts.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.openaitts_key.text()
        api = winobj.openaitts_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = winobj.openaitts_model.currentText()

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = api
        config.params["openaitts_model"] = model

        task = TestOpenaitts(parent=winobj, text="你好啊我的朋友")
        winobj.test_openaitts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        winobj.test_openaitts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_openaitts():
        key = winobj.openaitts_key.text()
        api = winobj.openaitts_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = winobj.openaitts_model.currentText()

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = api
        config.params["openaitts_model"] = model
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.openaitts_model.currentText()
        winobj.openaitts_model.clear()
        winobj.openaitts_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.openaitts_model.setCurrentText(current_text)
        config.settings['openaitts_model'] = t
        json.dump(config.settings, open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['openaitts_model']
        allmodels = config.settings['openaitts_model'].split(',')
        winobj.openaitts_model.clear()
        winobj.openaitts_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["openaitts_key"]:
            winobj.openaitts_key.setText(config.params["openaitts_key"])
        if config.params["openaitts_api"]:
            winobj.openaitts_api.setText(config.params["openaitts_api"])
        if config.params["openaitts_model"] and config.params['openaitts_model'] in allmodels:
            winobj.openaitts_model.setCurrentText(config.params["openaitts_model"])

    from videotrans.component import OpenAITTSForm
    winobj = config.child_forms.get('openaittsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = OpenAITTSForm()
    config.child_forms['openaittsw'] = winobj
    update_ui()

    winobj.set_openaitts.clicked.connect(save_openaitts)
    winobj.test_openaitts.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
