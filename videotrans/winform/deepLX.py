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

    def test():
        url = winobj.deeplx_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()

        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
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
        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import DeepLXForm
    winobj = DeepLXForm()
    config.child_forms['deeplx'] = winobj
    winobj.deeplx_address.setText(config.params.get("deeplx_address",''))
    winobj.deeplx_key.setText(config.params.get("deeplx_key",''))
    winobj.set_deeplx.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
