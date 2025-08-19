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
        url = winobj.deeplx_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()

        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPLX_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.deeplx_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.deeplx_key.text().strip()
        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepLXForm
    winobj = config.child_forms.get('deeplxw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLXForm()
    config.child_forms['deeplxw'] = winobj
    if config.params["deeplx_address"]:
        winobj.deeplx_address.setText(config.params["deeplx_address"])
    if config.params["deeplx_key"]:
        winobj.deeplx_key.setText(config.params["deeplx_key"])
    winobj.set_deeplx.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
