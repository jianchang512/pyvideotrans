from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


def open():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                import requests
                requests.get(config.params['recognapi_url'])
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
        if not winobj.recognapiform_address.text().strip():
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                           '必须填写http地址' if config.defaulelang == 'zh' else 'Must fill in the http address')
            return
        config.params['recognapi_url'] = winobj.recognapiform_address.text().strip()
        task = Test(parent=winobj)
        winobj.test.setText('测试连通性...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.recognapiform_address.text().strip()
        key = winobj.recognapiform_key.text().strip()
        if url:
            url = url.rstrip('/')
            url = 'http://' + url.replace('http://', '')
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import RecognAPIForm
    winobj = config.child_forms.get('recognapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = RecognAPIForm()
    config.child_forms['recognapiw'] = winobj
    if config.params["recognapi_url"]:
        winobj.recognapiform_address.setText(config.params["recognapi_url"])
    if config.params["recognapi_key"]:
        winobj.recognapiform_key.setText(config.params["recognapi_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
