


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
            return tools.show_error(
                tr("Please input AccessKey ID and AccessKey Secret"))
        config.params["ali_id"] = appid
        config.params["ali_key"] = miyue

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.ALI_INDEX)
        task.uito.connect(feed)
        task.start()

    from videotrans.component.set_form import AliForm

    winobj = AliForm()
    config.child_forms['ali'] = winobj
    if config.params.get("ali_id"):
        winobj.ali_id.setText(config.params.get("ali_id"))
    if config.params.get("ali_key"):
        winobj.ali_key.setText(config.params.get("ali_key"))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
