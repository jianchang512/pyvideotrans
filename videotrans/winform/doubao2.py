


def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.constants import LISTEN_TEXT
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.winform._helpers import make_feed_tts


    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_tts(winobj, "test")

    def test():
        appid = winobj.doubao2_appid.text().strip()
        access = winobj.doubao2_access.text().strip()
        if not appid or not access:
            return show_error(tr('Appid access and cluster are required'))
        params["doubao2_appid"] = appid
        params["doubao2_access"] = access
        params.save()
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('zh'),
            "role": "Vivi 2.0",
            "filename": config.TEMP_DIR + f"/{time.time()}-doubao2.wav",
            "tts_type": tts.DOUBAO2_TTS}],
                         language="zh",
                         tts_type=tts.DOUBAO2_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText(tr('Testing...'))

    def save():
        params["doubao2_appid"] = winobj.doubao2_appid.text().strip()
        params["doubao2_access"] = winobj.doubao2_access.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
