import builtins
import json
import os

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


# set chatgpt
def open():
    class TestOpenairecognapi(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                import requests
                proxyip = os.environ.get('http_proxy') or os.environ.get('https_proxy')
                proxies = {"http": proxyip, "https": proxyip}

                requests.get(config.params['openairecognapi_url'], proxies=proxies)
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(openairecognapiw, "ok",
                                              "测试可以连接到该API" if config.defaulelang == 'zh' else 'Tests can connect to this API')
        else:
            QtWidgets.QMessageBox.critical(openairecognapiw, config.transobj['anerror'], d)
        openairecognapiw.test_openairecognapi.setText(
            '测试能否连接' if config.defaulelang == 'zh' else 'Test for connectivity')

    def test():
        key = openairecognapiw.openairecognapi_key.text()
        prompt = openairecognapiw.openairecognapi_prompt.text()
        api = openairecognapiw.openairecognapi_url.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = openairecognapiw.openairecognapi_model.currentText()

        config.params["openairecognapi_key"] = key
        config.params["openairecognapi_url"] = api
        config.params["openairecognapi_model"] = model
        config.params["openairecognapi_prompt"] = prompt
        task = TestOpenairecognapi(parent=openairecognapiw)
        openairecognapiw.test_openairecognapi.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        openairecognapiw.test_openairecognapi.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_openairecognapi():
        key = openairecognapiw.openairecognapi_key.text()
        prompt = openairecognapiw.openairecognapi_prompt.text()
        api = openairecognapiw.openairecognapi_url.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = openairecognapiw.openairecognapi_model.currentText()

        config.params["openairecognapi_key"] = key
        config.params["openairecognapi_url"] = api
        config.params["openairecognapi_model"] = model
        config.params["openairecognapi_prompt"] = prompt
        config.getset_params(config.params)
        openairecognapiw.close()

    def setallmodels():
        t = openairecognapiw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = openairecognapiw.openairecognapi_model.currentText()
        openairecognapiw.openairecognapi_model.clear()
        openairecognapiw.openairecognapi_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            openairecognapiw.openairecognapi_model.setCurrentText(current_text)
        config.settings['openairecognapi_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['openairecognapi_model']
        allmodels = config.settings['openairecognapi_model'].split(',')
        openairecognapiw.openairecognapi_model.clear()
        openairecognapiw.openairecognapi_model.addItems(allmodels)
        openairecognapiw.edit_allmodels.setPlainText(allmodels_str)

        if config.params["openairecognapi_key"]:
            openairecognapiw.openairecognapi_key.setText(config.params["openairecognapi_key"])
        if config.params["openairecognapi_prompt"]:
            openairecognapiw.openairecognapi_prompt.setText(config.params["openairecognapi_prompt"])
        if config.params["openairecognapi_url"]:
            openairecognapiw.openairecognapi_url.setText(config.params["openairecognapi_url"])
        if config.params["openairecognapi_model"] and config.params['openairecognapi_model'] in allmodels:
            openairecognapiw.openairecognapi_model.setCurrentText(config.params["openairecognapi_model"])

    from videotrans.component import OpenaiRecognAPIForm
    openairecognapiw = config.child_forms.get('openairecognapiw')
    if openairecognapiw is not None:
        openairecognapiw.show()
        update_ui()
        openairecognapiw.raise_()
        openairecognapiw.activateWindow()
        return
    openairecognapiw = OpenaiRecognAPIForm()
    config.child_forms['openairecognapiw'] = openairecognapiw
    update_ui()
    openairecognapiw.set_openairecognapi.clicked.connect(save_openairecognapi)
    openairecognapiw.test_openairecognapi.clicked.connect(test)
    openairecognapiw.edit_allmodels.textChanged.connect(setallmodels)
    openairecognapiw.show()
