def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr
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

        config.params["libre_address"] = url
        config.params["libre_key"] = key
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.LIBRE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()
        config.params["libre_address"] = url
        config.params["libre_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import LibreForm
    winobj = LibreForm()
    config.child_forms['libre'] = winobj
    winobj.address.setText(config.params.get("libre_address",''))
    winobj.key.setText(config.params.get("libre_key",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
