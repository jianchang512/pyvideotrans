def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        if not key:
            return tools.show_error(tr("Please input auth Secret"))

        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPL_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import DeepLForm
    winobj = DeepLForm()
    config.child_forms['deepl'] = winobj
    if config.params['deepl_authkey']:
        winobj.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        winobj.deepl_api.setText(config.params['deepl_api'])
    if config.params['deepl_gid']:
        winobj.deepl_gid.setText(config.params['deepl_gid'])
    winobj.set_deepl.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
