def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        miyue = winobj.miyue.text()
        config.params["trans_api_url"] = url
        config.params["trans_secret"] = miyue
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import TransapiForm
    winobj = config.child_forms.get('transapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = TransapiForm()
    config.child_forms['transapiw'] = winobj
    if config.params["trans_api_url"]:
        winobj.api_url.setText(config.params["trans_api_url"])
    if config.params["trans_secret"]:
        winobj.miyue.setText(config.params["trans_secret"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
