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
        params["recognapi_url"] = _fix_url(winobj.recognapiform_address.text().strip())
        params["recognapi_key"] = winobj.recognapiform_key.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.CUSTOM_API)
        task.uito.connect(feed)
        task.start()

    def save():
        params["recognapi_url"] = _fix_url(winobj.recognapiform_address.text().strip()).rstrip('/')
        params["recognapi_key"] = winobj.recognapiform_key.text().strip()
        params.save()
        winobj.close()

    winobj.recognapiform_address.setText(str(params.get("recognapi_url", '')))
    winobj.recognapiform_key.setText(str(params.get("recognapi_key", '')))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
