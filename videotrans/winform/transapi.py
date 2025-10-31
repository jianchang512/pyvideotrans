def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,logs
    from videotrans.configure import config
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
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        winobj.test.setText(tr("Testing..."))

        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import TransapiForm
    winobj = TransapiForm()
    config.child_forms['transapi'] = winobj
    winobj.api_url.setText(config.params.get("trans_api_url",''))
    winobj.miyue.setText(config.params.get("trans_secret",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
