def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,logs
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.recognapiform_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url

        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)

        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.CUSTOM_API)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.recognapiform_address.text().strip()

        if not url.startswith('http'):
            url = 'http://' + url
        url = url.rstrip('/')
        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import RecognAPIForm
    winobj = RecognAPIForm()
    config.child_forms['recognapi'] = winobj
    winobj.recognapiform_address.setText(config.params.get("recognapi_url",''))
    winobj.recognapiform_key.setText(config.params.get("recognapi_key",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
