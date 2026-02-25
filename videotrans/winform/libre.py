def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr,settings,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()

        params["libre_address"] = url
        params["libre_key"] = key
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.LIBRE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()
        params["libre_address"] = url
        params["libre_key"] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import LibreForm
    winobj = LibreForm()
    app_cfg.child_forms['libre'] = winobj
    winobj.address.setText(params.get("libre_address",''))
    winobj.key.setText(params.get("libre_key",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
