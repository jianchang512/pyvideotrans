from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config


# 翻译

# set deepl key
def openwin():
    class TestTask(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.DEEPL_INDEX,
                                      text_list=raw,
                                      target_code="en",
                                      source_code="zh-cn",
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
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        if not key:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  '必须填写 密钥' if config.defaulelang == 'zh' else 'Please input auth Secret')

        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
    def save():
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepLForm
    winobj = config.child_forms.get('deeplw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLForm()
    config.child_forms['deeplw'] = winobj
    if config.params['deepl_authkey']:
        winobj.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        winobj.deepl_api.setText(config.params['deepl_api'])
    if config.params['deepl_gid']:
        winobj.deepl_gid.setText(config.params['deepl_gid'])
    winobj.set_deepl.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
