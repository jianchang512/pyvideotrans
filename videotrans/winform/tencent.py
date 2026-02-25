def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools

    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        SecretId = winobj.tencent_SecretId.text().strip()
        SecretKey = winobj.tencent_SecretKey.text().strip()
        term = winobj.tencent_term.text().strip()
        if not SecretId or not SecretKey:
            return tools.show_error(
                tr("Please input SecretId and SecretKey"))
        params["tencent_SecretId"] = SecretId
        params["tencent_SecretKey"] = SecretKey
        params["tencent_termlist"] = term
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TENCENT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        SecretId = winobj.tencent_SecretId.text().strip()
        SecretKey = winobj.tencent_SecretKey.text().strip()
        term = winobj.tencent_term.text().strip()
        params["tencent_SecretId"] = SecretId
        params["tencent_SecretKey"] = SecretKey
        params["tencent_termlist"] = term
        params.save()
        winobj.close()

    from videotrans.component.set_form import TencentForm
    winobj = TencentForm()
    app_cfg.child_forms['tencent'] = winobj
    if params["tencent_SecretId"]:
        winobj.tencent_SecretId.setText(params["tencent_SecretId"])
    if params["tencent_SecretKey"]:
        winobj.tencent_SecretKey.setText(params["tencent_SecretKey"])
    if params["tencent_termlist"]:
        winobj.tencent_term.setText(params["tencent_termlist"])
    winobj.set_tencent.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
