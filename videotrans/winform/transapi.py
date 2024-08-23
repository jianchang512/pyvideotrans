from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


def open():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            from videotrans.translator.transapi import trans
            try:
                t = trans(self.text, target_language="en", set_p=False, is_test=True, source_code="zh")
                self.uito.emit(f"ok:{self.text}\n{str(t)}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d.startswith("ok:"):
            QtWidgets.QMessageBox.information(config.transapiw, "ok", d[3:])
        else:
            QtWidgets.QMessageBox.critical(config.transapiw, config.transobj['anerror'], d)
        config.transapiw.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = config.transapiw.api_url.text()
        config.params["ttsapi_url"] = url
        if not url:
            return QtWidgets.QMessageBox.critical(config.transapiw, config.transobj['anerror'],
                                                  "必须填写自定义翻译的url" if config.defaulelang == 'zh' else "The url of the custom translation must be filled in")
        url = config.transapiw.api_url.text()
        miyue = config.transapiw.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        task = Test(parent=config.transapiw, text="你好啊我的朋友")
        config.transapiw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = config.transapiw.api_url.text()
        miyue = config.transapiw.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        config.getset_params(config.params)
        config.transapiw.close()

    from videotrans.component import TransapiForm
    if config.transapiw is not None:
        config.transapiw.show()
        config.transapiw.raise_()
        config.transapiw.activateWindow()
        return
    config.transapiw = TransapiForm()
    if config.params["trans_api_url"]:
        config.transapiw.api_url.setText(config.params["trans_api_url"])
    if config.params["trans_secret"]:
        config.transapiw.miyue.setText(config.params["trans_secret"])

    config.transapiw.save.clicked.connect(save)
    config.transapiw.test.clicked.connect(test)
    config.transapiw.show()
