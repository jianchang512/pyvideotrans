import builtins
import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


# set chatgpt
def open():
    class TestOpenaitts(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            from videotrans.tts.openaitts import get_voice
            try:
                role = 'alloy'

                get_voice(
                    text=self.text,
                    role=role,
                    language="zh-CN",
                    rate='+0%',
                    set_p=False, filename=config.TEMP_HOME + "/test.mp3")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(openaittsw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(openaittsw, "OK", d[3:])
        openaittsw.test_openaitts.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = openaittsw.openaitts_key.text()
        api = openaittsw.openaitts_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = openaittsw.openaitts_model.currentText()

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = api
        config.params["openaitts_model"] = model

        task = TestOpenaitts(parent=openaittsw, text="你好啊我的朋友")
        openaittsw.test_openaitts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        openaittsw.test_openaitts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_openaitts():
        key = openaittsw.openaitts_key.text()
        api = openaittsw.openaitts_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = openaittsw.openaitts_model.currentText()

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = api
        config.params["openaitts_model"] = model
        config.getset_params(config.params)
        openaittsw.close()

    def setallmodels():
        t = openaittsw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = openaittsw.openaitts_model.currentText()
        openaittsw.openaitts_model.clear()
        openaittsw.openaitts_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            openaittsw.openaitts_model.setCurrentText(current_text)
        config.settings['openaitts_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['openaitts_model']
        allmodels = config.settings['openaitts_model'].split(',')
        openaittsw.openaitts_model.clear()
        openaittsw.openaitts_model.addItems(allmodels)
        openaittsw.edit_allmodels.setPlainText(allmodels_str)

        if config.params["openaitts_key"]:
            openaittsw.openaitts_key.setText(config.params["openaitts_key"])
        if config.params["openaitts_api"]:
            openaittsw.openaitts_api.setText(config.params["openaitts_api"])
        if config.params["openaitts_model"] and config.params['openaitts_model'] in allmodels:
            openaittsw.openaitts_model.setCurrentText(config.params["openaitts_model"])

    from videotrans.component import OpenAITTSForm
    openaittsw = config.child_forms.get('openaittsw')
    if openaittsw is not None:
        openaittsw.show()
        update_ui()
        openaittsw.raise_()
        openaittsw.activateWindow()
        return
    openaittsw = OpenAITTSForm()
    config.child_forms['openaittsw'] = openaittsw
    update_ui()

    openaittsw.set_openaitts.clicked.connect(save_openaitts)
    openaittsw.test_openaitts.clicked.connect(test)
    openaittsw.edit_allmodels.textChanged.connect(setallmodels)
    openaittsw.show()
