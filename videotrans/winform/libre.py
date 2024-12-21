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
                text = translator.run(translate_type=translator.LIBRE_INDEX,
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
        url = winobj.address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()

        config.params["libre_address"] = url
        config.params["libre_key"] = key


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url    
        key = winobj.key.text().strip()
        config.params["libre_address"] = url
        config.params["libre_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import LibreForm
    winobj = config.child_forms.get('librew')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = LibreForm()
    config.child_forms['librew'] = winobj
    if config.params["libre_address"]:
        winobj.address.setText(config.params["libre_address"])
    if config.params["libre_key"]:
        winobj.key.setText(config.params["libre_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
