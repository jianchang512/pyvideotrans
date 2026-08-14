

def openwin():
    from videotrans.configure.contants import LISTEN_TEXT
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import KokoroForm

    winobj = KokoroForm()
    app_cfg.child_forms['kokoro'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr("Test"))

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url.rstrip('/')

    def test():
        params['kokoro_api'] = _fix_url(winobj.kokoro_address.text().strip())
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('en'),
            "role": "af_alloy",
            "filename": config.TEMP_DIR + f"/{time.time()}-kokoro.wav",
            "tts_type": tts.KOKORO_TTS}],
                         language="en",
                         tts_type=tts.KOKORO_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["kokoro_api"] = _fix_url(winobj.kokoro_address.text().strip())
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()

    winobj.kokoro_address.setText(str(params.get("kokoro_api",'')))
    winobj.set_kokoro.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
