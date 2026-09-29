

def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt


    winobj = get_cls(Path(__file__).stem)()

    feed = make_feed_stt(winobj, "test")

    def test():
        apikey = winobj.apikey.text().strip()
        if not apikey:
            show_error(tr("Must fill in the API Key"))
            return
        params["deepgram_apikey"] = apikey
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.Deepgram, model_name="whisper-large")
        task.uito.connect(feed)
        task.start()

    def save():
        apikey = winobj.apikey.text().strip()
        if not apikey:
            show_error(tr("Must fill in the API Key"))
            return
        params["deepgram_apikey"] = apikey
        params.save()
        set_process(text='', type="refreshmodel_list")
        winobj.close()

    winobj.apikey.setText(str(params.get("deepgram_apikey", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
