from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


def open():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, language=None, role=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                import requests
                res = requests.get(config.params['zh_recogn_api'])
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
        if not winobj.zhrecogn_address.text().strip():
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], '必须填写http地址')
            return
        config.params['zh_recogn_api'] = winobj.zhrecogn_address.text().strip()
        task = Test(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.zhrecogn_address.text().strip()
        if key:
            key = key.rstrip('/')
            key = 'http://' + key.replace('http://', '')
        config.params["zh_recogn_api"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import ZhrecognForm
    winobj = config.child_forms.get('zhrecognw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ZhrecognForm()
    config.child_forms['zhrecognw'] = winobj
    if config.params["zh_recogn_api"]:
        winobj.zhrecogn_address.setText(config.params["zh_recogn_api"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
