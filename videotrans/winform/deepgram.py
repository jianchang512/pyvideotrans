def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt
    from videotrans.component.set_form import DeepgramForm

    winobj = DeepgramForm()
    app_cfg.child_forms['deepgram'] = winobj

    feed = make_feed_stt(winobj, "test")

    def test():
        apikey = winobj.apikey.text().strip()
        if not apikey:
            tools.show_error(tr("Must fill in the API Key"))
            return
        params["deepgram_apikey"] = apikey
        params["deepgram_utt"] = winobj.utt.text().strip() or 200
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.Deepgram, model_name="whisper-large")
        task.uito.connect(feed)
        task.start()

    def save():
        apikey = winobj.apikey.text().strip()
        if not apikey:
            tools.show_error(tr("Must fill in the API Key"))
            return
        params["deepgram_apikey"] = apikey
        params["deepgram_utt"] = winobj.utt.text().strip() or 200
        params.save()
        tools.set_process(text='', type="refreshmodel_list")
        winobj.close()

    winobj.apikey.setText(str(params.get("deepgram_apikey", '')))
    winobj.utt.setText(str(params.get("deepgram_utt", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
