def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        params["trans_api_url"] = url
        params["trans_secret"] = miyue
        winobj.test.setText(tr("Testing..."))

        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        params["trans_api_url"] = url
        params["trans_secret"] = miyue
        params.save()
        winobj.close()

    from videotrans.component.set_form import TransapiForm
    winobj = TransapiForm()
    app_cfg.child_forms['transapi'] = winobj
    winobj.api_url.setText(params.get("trans_api_url",''))
    winobj.miyue.setText(params.get("trans_secret",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
