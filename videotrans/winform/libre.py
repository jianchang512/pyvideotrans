

def openwin():
    from pathlib import Path
    from videotrans.winform import get_cls
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
        params["libre_address"] = _fix_url(winobj.address.text().strip())
        params["libre_key"] = winobj.key.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.LIBRE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["libre_address"] = _fix_url(winobj.address.text().strip())
        params["libre_key"] = winobj.key.text().strip()
        params.save()
        winobj.close()

    winobj.address.setText(str(params.get("libre_address", '')))
    winobj.key.setText(str(params.get("libre_key", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
