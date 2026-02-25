def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
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
        params["recognapi_url"] = url
        params["recognapi_key"] = key
        params.save()

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
        params["recognapi_url"] = url
        params["recognapi_key"] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import RecognAPIForm
    winobj = RecognAPIForm()
    app_cfg.child_forms['recognapi'] = winobj
    winobj.recognapiform_address.setText(params.get("recognapi_url",''))
    winobj.recognapiform_key.setText(params.get("recognapi_key",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
