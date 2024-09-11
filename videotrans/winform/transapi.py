from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config


def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):

            try:
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = translator.run(translate_type=translator.TRANSAPI_INDEX, text_list=raw,
                                      source_code='zh-cn' if config.defaulelang != 'zh' else "en",
                                      target_language_name="en" if config.defaulelang != 'zh' else "zh", is_test=True)
                self.uito.emit(f"ok:{self.raw}\n{str(text)}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d.startswith("ok:"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = winobj.api_url.text()
        config.params["ttsapi_url"] = url
        if not url:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  "必须填写自定义翻译的url" if config.defaulelang == 'zh' else "The url of the custom translation must be filled in")
        url = winobj.api_url.text()
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        task = Test(parent=winobj, text="你好啊我的朋友")
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text()
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import TransapiForm
    winobj = config.child_forms.get('transapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = TransapiForm()
    config.child_forms['transapiw'] = winobj
    if config.params["trans_api_url"]:
        winobj.api_url.setText(config.params["trans_api_url"])
    if config.params["trans_secret"]:
        winobj.miyue.setText(config.params["trans_secret"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
