def openwin():
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.winform._helpers import make_feed_tts
    from videotrans.component.set_form import Doubao2TTSForm

    winobj = Doubao2TTSForm()
    app_cfg.child_forms['doubao2'] = winobj
    winobj.update_ui()

    feed = make_feed_tts(winobj, "test")

    def test():
        appid = winobj.doubao2_appid.text().strip()
        access = winobj.doubao2_access.text().strip()
        if not appid or not access:
            return tools.show_error(tr('Appid access and cluster are required'))
        params["doubao2_appid"] = appid
        params["doubao2_access"] = access
        params.save()
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
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
    winobj.show()
