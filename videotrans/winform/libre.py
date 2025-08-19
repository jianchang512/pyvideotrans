def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()

        config.params["libre_address"] = url
        config.params["libre_key"] = key
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSrtTrans(parent=winobj, translator_type=translator.LIBRE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        key = winobj.key.text().strip()
        config.params["libre_address"] = url
        config.params["libre_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import LibreForm
    winobj = config.child_forms.get('librew')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = LibreForm()
    config.child_forms['librew'] = winobj
    if config.params["libre_address"]:
        winobj.address.setText(config.params["libre_address"])
    if config.params["libre_key"]:
        winobj.key.setText(config.params["libre_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
