def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt
    from videotrans.component.set_form import ParakeetForm

    winobj = ParakeetForm()
    app_cfg.child_forms['parakeet'] = winobj
    winobj.update_ui()

    feed = make_feed_stt(winobj, "test")

    def _fix_url(url):
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.replace('/audio/transcriptions', '').strip('/')
        if not url.endswith('/v1'):
            url = url + '/v1'
        return url

    def test():
        url = winobj.parakeet_address.text().strip().strip('/')
        if not url:
            return
        params["parakeet_address"] = _fix_url(url)
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.PARAKEET)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.parakeet_address.text().strip()
        if not url:
            return
        params["parakeet_address"] = _fix_url(url)
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    winobj.set_btn.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
