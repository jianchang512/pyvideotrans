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
            QtWidgets.QMessageBox.information(config.zhrecognw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.zhrecognw, config.transobj['anerror'], d)
        config.zhrecognw.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        if not config.zhrecognw.zhrecogn_address.text().strip():
            QtWidgets.QMessageBox.critical(config.zhrecognw, config.transobj['anerror'], '必须填写http地址')
            return
        config.params['zh_recogn_api'] = config.zhrecognw.zhrecogn_address.text().strip()
        task = Test(parent=config.zhrecognw)
        config.zhrecognw.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = config.zhrecognw.zhrecogn_address.text().strip()
        key = key.rstrip('/')
        key = 'http://' + key.replace('http://', '')
        config.params["zh_recogn_api"] = key
        config.getset_params(config.params)
        config.zhrecognw.close()

    from videotrans.component import ZhrecognForm
    if config.zhrecognw is not None:
        config.zhrecognw.show()
        config.zhrecognw.raise_()
        config.zhrecognw.activateWindow()
        return
    config.zhrecognw = ZhrecognForm()
    if config.params["zh_recogn_api"]:
        config.zhrecognw.zhrecogn_address.setText(config.params["zh_recogn_api"])
    config.zhrecognw.set.clicked.connect(save)
    config.zhrecognw.test.clicked.connect(test)
    config.zhrecognw.show()
