def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator
    from videotrans.component.set_form import TransapiForm

    winobj = TransapiForm()
    app_cfg.child_forms['transapi'] = winobj

    feed = make_feed_translator(winobj, "test")

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["trans_api_url"] = _fix_url(winobj.api_url.text().strip())
        params["trans_secret"] = winobj.miyue.text()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["trans_api_url"] = _fix_url(winobj.api_url.text().strip())
        params["trans_secret"] = winobj.miyue.text()
        params.save()
        winobj.close()

    winobj.api_url.setText(params.get("trans_api_url", ''))
    winobj.miyue.setText(str(params.get("trans_secret", '')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
