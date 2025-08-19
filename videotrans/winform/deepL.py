def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        if not key:
            return tools.show_error('必须填写 密钥' if config.defaulelang == 'zh' else 'Please input auth Secret', False)

        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
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

    from videotrans.component import DeepLForm
    winobj = config.child_forms.get('deeplw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLForm()
    config.child_forms['deeplw'] = winobj
    if config.params['deepl_authkey']:
        winobj.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        winobj.deepl_api.setText(config.params['deepl_api'])
    if config.params['deepl_gid']:
        winobj.deepl_gid.setText(config.params['deepl_gid'])
    winobj.set_deepl.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
