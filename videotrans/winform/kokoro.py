def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.kokoro_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params['kokoro_api'] = url
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": 'hello,my friend',
            "role": "af_alloy",
            "filename": TEMP_DIR + f"/{time.time()}-kokoro.wav",
            "tts_type": tts.KOKORO_TTS}],
                         language="en",
                         tts_type=tts.KOKORO_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.kokoro_address.text().strip()
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        params["kokoro_api"] = url
        params.save()
        winobj.close()

    from videotrans.component.set_form import KokoroForm

    winobj = KokoroForm()
    app_cfg.child_forms['kokoro'] = winobj
    winobj.kokoro_address.setText(params.get("kokoro_api",''))
    winobj.set_kokoro.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
