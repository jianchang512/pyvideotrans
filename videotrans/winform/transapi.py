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
        params["transapi_url"] = _fix_url(winobj.api_url.text().strip())
        params["transapi_key"] = winobj.miyue.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TRANSAPI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["transapi_url"] = _fix_url(winobj.api_url.text().strip())
        params["transapi_key"] = winobj.miyue.text().strip()
        params.save()
        winobj.close()

    winobj.api_url.setText(str(params.get("transapi_url", '')))
    winobj.miyue.setText(str(params.get("transapi_key", '')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
