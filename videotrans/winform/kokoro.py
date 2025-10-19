def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr
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
        config.params['kokoro_api'] = url
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": 'hello,my friend',
            "role": "af_alloy",
            "filename": config.TEMP_HOME + f"/{time.time()}-kokoro.wav",
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
        config.params["kokoro_api"] = url
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import KokoroForm

    winobj = KokoroForm()
    config.child_forms['kokoro'] = winobj
    winobj.kokoro_address.setText(config.params.get("kokoro_api",''))
    winobj.set_kokoro.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
