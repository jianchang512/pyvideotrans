def openwin():
    from PySide6 import QtWidgets
    from videotrans import recognition
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            tools.show_error(tr("Must fill in the API Key"))
            return
        params["deepgram_apikey"] = apikey
        params["deepgram_utt"] = 200 if utt else 200
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.Deepgram, model_name="whisper-large")
        task.uito.connect(feed)
        task.start()

    def save():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            tools.show_error(tr("Must fill in the API Key"))
            return

        params["deepgram_apikey"] = apikey
        params["deepgram_utt"] = 200 if utt else 200
        params.save()
        winobj.close()

    from videotrans.component.set_form import DeepgramForm
    winobj = DeepgramForm()
    app_cfg.child_forms['deepgram'] = winobj
    winobj.apikey.setText(params.get("deepgram_apikey",''))
    winobj.utt.setText(str(params.get("deepgram_utt",'')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
