def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator


    winobj = get_cls(Path(__file__).stem)()

    feed = make_feed_translator(winobj, "test")

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["trans_api_url"] = _fix_url(winobj.api_url.text().strip())
        params["trans_secret"] = winobj.miyue.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["trans_api_url"] = _fix_url(winobj.api_url.text().strip())
        params["trans_secret"] = winobj.miyue.text().strip()
        params.save()
        winobj.close()

    winobj.api_url.setText(str(params.get("trans_api_url", '')))
    winobj.miyue.setText(str(params.get("trans_secret", '')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
