from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                import requests
                requests.get(config.params['stt_url'])
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok",
                                              "测试可以连接到该API" if config.defaulelang == 'zh' else 'Tests can connect to this API')
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试能否连接' if config.defaulelang == 'zh' else 'Test for connectivity')

    def test():
        if not winobj.stt_url.text().strip():
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                           '必须填写http地址' if config.defaulelang == 'zh' else 'Must fill in the http address')
            return
        config.params['stt_url'] = winobj.stt_url.text().strip()
        task = Test(parent=winobj)
        winobj.test.setText('测试连通性...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.stt_url.text().strip()
        model = winobj.stt_model.currentText()
        if url:
            url = url.rstrip('/')
            url = 'http://' + url.replace('http://', '')
            
        config.params["stt_url"] = url
        config.params["stt_model"] = model
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import SttAPIForm
    winobj = config.child_forms.get('sttw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = SttAPIForm()
    config.child_forms['sttw'] = winobj
    if config.params["stt_url"]:
        winobj.stt_url.setText(config.params["stt_url"])
    if config.params["stt_model"]:
        winobj.stt_model.setCurrentText(config.params["stt_model"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
