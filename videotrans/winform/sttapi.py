def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt
    from videotrans.component.set_form import SttAPIForm

    winobj = SttAPIForm()
    app_cfg.child_forms['sttapi'] = winobj

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

    winobj.stt_url.setText(params.get("stt_url", ''))
    winobj.stt_model.setCurrentText(params.get("stt_model", ''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
