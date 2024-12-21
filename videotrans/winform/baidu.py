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
                text = translator.run(translate_type=translator.BAIDU_INDEX,
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
    def save_baidu():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue
        config.getset_params(config.params)
        winobj.close()
    def test():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        if not appid or not miyue:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  '必须填写 appid 和 密钥 等信息' if config.defaulelang == 'zh' else 'Please input appid and Secret')
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue


        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    from videotrans.component import BaiduForm
    winobj = config.child_forms.get('baiduw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = BaiduForm()
    config.child_forms['baiduw'] = winobj
    if config.params["baidu_appid"]:
        winobj.baidu_appid.setText(config.params["baidu_appid"])
    if config.params["baidu_miyue"]:
        winobj.baidu_miyue.setText(config.params["baidu_miyue"])
    winobj.set_badiu.clicked.connect(save_baidu)
    winobj.test.clicked.connect(test)
    winobj.show()
