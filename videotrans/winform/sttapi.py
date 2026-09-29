def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt
    from pathlib import Path


    winobj = get_cls(Path(__file__).stem)()

    feed = make_feed_stt(winobj, "test")

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params['sttapi_url'] = _fix_url(winobj.sttapi_url.text().strip())
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.STT_API, model_name=winobj.stt_model.currentText())
        task.uito.connect(feed)
        task.start()

    def save():
        params["sttapi_url"] = _fix_url(winobj.sttapi_url.text().strip()).rstrip('/')
        params.save()
        winobj.close()

    winobj.sttapi_url.setText(str(params.get("sttapi_url", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
