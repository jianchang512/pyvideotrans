def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.recognapiform_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)

        winobj.test.setText('测试中...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSTT(parent=winobj, recogn_type=recognition.CUSTOM_API)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.recognapiform_address.text().strip()
        if tools.check_local_api(url) is not True:
            return

        if not url.startswith('http'):
            url = 'http://' + url
        url = url.rstrip('/')
        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import RecognAPIForm
    winobj = config.child_forms.get('recognapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = RecognAPIForm()
    config.child_forms['recognapiw'] = winobj
    if config.params["recognapi_url"]:
        winobj.recognapiform_address.setText(config.params["recognapi_url"])
    if config.params["recognapi_key"]:
        winobj.recognapiform_key.setText(config.params["recognapi_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
