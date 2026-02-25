


def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def save():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        params["ali_id"] = appid
        params["ali_key"] = miyue
        params.save()
        winobj.close()

    def test():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        if not appid or not miyue:
            return tools.show_error(
                tr("Please input AccessKey ID and AccessKey Secret"))
        params["ali_id"] = appid
        params["ali_key"] = miyue

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.ALI_INDEX)
        task.uito.connect(feed)
        task.start()

    from videotrans.component.set_form import AliForm

    winobj = AliForm()
    app_cfg.child_forms['ali'] = winobj
    if params.get("ali_id"):
        winobj.ali_id.setText(params.get("ali_id"))
    if params.get("ali_key"):
        winobj.ali_key.setText(params.get("ali_key"))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
