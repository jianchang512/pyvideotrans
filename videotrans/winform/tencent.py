def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr
    from videotrans.configure import config
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
        config.params["tencent_SecretId"] = SecretId
        config.params["tencent_SecretKey"] = SecretKey
        config.params["tencent_termlist"] = term
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TENCENT_INDEX)
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

    from videotrans.component.set_form import TencentForm
    winobj = TencentForm()
    config.child_forms['tencent'] = winobj
    if config.params["tencent_SecretId"]:
        winobj.tencent_SecretId.setText(config.params["tencent_SecretId"])
    if config.params["tencent_SecretKey"]:
        winobj.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
    if config.params["tencent_termlist"]:
        winobj.tencent_term.setText(config.params["tencent_termlist"])
    winobj.set_tencent.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
