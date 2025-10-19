def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.configure.config import tr
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(
            tr("Test"))

    def test():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token')
            return

        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.DOUBAO_API)
        task.uito.connect(feed)
        task.start()

    def save():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token')
            return
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        winobj.close()

    from videotrans.component.set_form import DoubaoForm
    winobj = DoubaoForm()
    config.child_forms['doubao'] = winobj
    winobj.doubao_appid.setText(config.params.get("doubao_appid",''))
    winobj.doubao_access.setText(config.params.get("doubao_access",''))

    winobj.set_save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
