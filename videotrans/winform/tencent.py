from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config


def openwin():
    class TestTask(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.TENCENT_INDEX,
                                      text_list=raw,
                                      source_code="zh-cn",
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

    def test():
        SecretId = winobj.tencent_SecretId.text().strip()
        SecretKey = winobj.tencent_SecretKey.text().strip()
        term = winobj.tencent_term.text().strip()
        if not SecretId or not SecretKey:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  '必须填写ID 和 Key等信息' if config.defaulelang == 'zh' else 'Please input SecretId and SecretKey')
        config.params["tencent_SecretId"] = SecretId
        config.params["tencent_SecretKey"] = SecretKey
        config.params["tencent_termlist"] = term


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        SecretId = winobj.tencent_SecretId.text().strip()
        SecretKey = winobj.tencent_SecretKey.text().strip()
        term = winobj.tencent_term.text().strip()
        config.params["tencent_SecretId"] = SecretId
        config.params["tencent_SecretKey"] = SecretKey
        config.params["tencent_termlist"] = term
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import TencentForm
    winobj = config.child_forms.get('tencentw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = TencentForm()
    config.child_forms['tencentw'] = winobj
    if config.params["tencent_SecretId"]:
        winobj.tencent_SecretId.setText(config.params["tencent_SecretId"])
    if config.params["tencent_SecretKey"]:
        winobj.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
    if config.params["tencent_termlist"]:
        winobj.tencent_term.setText(config.params["tencent_termlist"])
    winobj.set_tencent.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
