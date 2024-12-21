from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config
from videotrans.util import tools

def openwin():
    class TestTask(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.DEEPLX_INDEX,
                                      text_list=raw,
                                      source_code="zh-cn",
                                      target_code="en",
                                      is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.deeplx_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()

        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.deeplx_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url    
        key = winobj.deeplx_key.text().strip()
        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepLXForm
    winobj = config.child_forms.get('deeplxw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLXForm()
    config.child_forms['deeplxw'] = winobj
    if config.params["deeplx_address"]:
        winobj.deeplx_address.setText(config.params["deeplx_address"])
    if config.params["deeplx_key"]:
        winobj.deeplx_key.setText(config.params["deeplx_key"])
    winobj.set_deeplx.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
