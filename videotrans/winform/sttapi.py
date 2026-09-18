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
        params['stt_url'] = _fix_url(winobj.stt_url.text().strip())
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.STT_API, model_name=winobj.stt_model.currentText())
        task.uito.connect(feed)
        task.start()

    def save():
        params["stt_url"] = _fix_url(winobj.stt_url.text().strip()).rstrip('/')
        params["stt_model"] = winobj.stt_model.currentText()
        params.save()
        winobj.close()

    winobj.stt_url.setText(str(params.get("stt_url", '')))
    winobj.stt_model.setCurrentText(str(params.get("stt_model", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
