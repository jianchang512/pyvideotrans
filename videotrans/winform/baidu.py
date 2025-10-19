def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.configure.config import tr
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

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
            return tools.show_error(
                tr("Please input appid and Secret"))
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.BAIDU_INDEX)
        task.uito.connect(feed)
        task.start()

    from videotrans.component.set_form import BaiduForm

    winobj = BaiduForm()
    config.child_forms['baidu'] = winobj
    if config.params.get("baidu_appid",''):
        winobj.baidu_appid.setText(config.params.get("baidu_appid",''))
    if config.params.get("baidu_miyue",''):
        winobj.baidu_miyue.setText(config.params.get("baidu_miyue",''))
    winobj.set_badiu.clicked.connect(save_baidu)
    winobj.test.clicked.connect(test)
    winobj.show()
