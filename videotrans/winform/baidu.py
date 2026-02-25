def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.configure.config import tr,settings,params,app_cfg
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def save_baidu():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        params["baidu_appid"] = appid
        params["baidu_miyue"] = miyue
        params.save()
        winobj.close()

    def test():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        if not appid or not miyue:
            return tools.show_error(
                tr("Please input appid and Secret"))
        params["baidu_appid"] = appid
        params["baidu_miyue"] = miyue

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.BAIDU_INDEX)
        task.uito.connect(feed)
        task.start()

    from videotrans.component.set_form import BaiduForm

    winobj = BaiduForm()
    app_cfg.child_forms['baidu'] = winobj
    if params.get("baidu_appid",''):
        winobj.baidu_appid.setText(params.get("baidu_appid",''))
    if params.get("baidu_miyue",''):
        winobj.baidu_miyue.setText(params.get("baidu_miyue",''))
    winobj.set_badiu.clicked.connect(save_baidu)
    winobj.test.clicked.connect(test)
    winobj.show()
