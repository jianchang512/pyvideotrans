from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config


# set baidu
def openwin():
    class TestTask(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.ALI_INDEX,
                                      text_list=raw,
                                      source_code="zh",
                                      target_code="en", is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')
    def save():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        config.params["ali_id"] = appid
        config.params["ali_key"] = miyue
        config.getset_params(config.params)
        winobj.close()
    def test():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        if not appid or not miyue:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  '必须填写 AccessKey ID 和 AccessKey Secret 等信息' if config.defaulelang == 'zh' else 'Please input AccessKey ID and AccessKey Secret')
        config.params["ali_id"] = appid
        config.params["ali_key"] = miyue


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    from videotrans.component import AliForm
    winobj = config.child_forms.get('aliw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AliForm()
    config.child_forms['aliw'] = winobj
    if config.params["ali_id"]:
        winobj.ali_id.setText(config.params["ali_id"])
    if config.params["ali_key"]:
        winobj.ali_key.setText(config.params["ali_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
