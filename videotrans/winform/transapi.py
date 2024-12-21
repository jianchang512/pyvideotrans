from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config
from videotrans.util import tools

def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):

            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.TRANSAPI_INDEX, text_list=raw,
                                      source_code='zh-cn',
                                      target_code="en", is_test=True)
                self.uito.emit(f"ok:{raw}\n{str(text)}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        task = Test(parent=winobj, text="你好啊我的朋友")
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
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
