def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.deeplx_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()

        params["deeplx_address"] = url
        params["deeplx_key"] = key
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPLX_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.deeplx_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()
        params["deeplx_address"] = url
        params["deeplx_key"] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import DeepLXForm
    winobj = DeepLXForm()
    app_cfg.child_forms['deeplx'] = winobj
    winobj.deeplx_address.setText(params.get("deeplx_address",''))
    winobj.deeplx_key.setText(params.get("deeplx_key",''))
    winobj.set_deeplx.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
