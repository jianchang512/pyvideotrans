def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(
            '测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token', False)
            return

        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSTT(parent=winobj, recogn_type=recognition.DOUBAO_API)
        task.uito.connect(feed)
        task.start()

    def save():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token', False)
            return
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        winobj.close()

    from videotrans.component import DoubaoForm
    winobj = config.child_forms.get('doubaow')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DoubaoForm()
    config.child_forms['doubaow'] = winobj
    if config.params["doubao_appid"]:
        winobj.doubao_appid.setText(config.params["doubao_appid"])
    if config.params["doubao_access"]:
        winobj.doubao_access.setText(config.params["doubao_access"])

    winobj.set_save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
