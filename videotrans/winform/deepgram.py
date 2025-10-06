def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr
    from videotrans import recognition
    from videotrans.configure import config
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
        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
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

        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepgramForm
    winobj = DeepgramForm()
    config.child_forms['deepgram'] = winobj
    winobj.apikey.setText(config.params.get("deepgram_apikey",''))
    winobj.utt.setText(str(config.params.get("deepgram_utt",'')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
