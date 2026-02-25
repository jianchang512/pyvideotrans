def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,app_cfg,params,settings,logger
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
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params['whisperx_api'] = url
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.WHISPERX_API, model_name='tiny')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url

        url = url.rstrip('/')

        params["whisperx_api"] = url
        params.save()
        winobj.close()

    from videotrans.component.set_form import WhisperXAPIForm
    winobj = WhisperXAPIForm()
    app_cfg.child_forms['whisperx'] = winobj
    winobj.api_url.setText(params.get("whisperx_api",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
