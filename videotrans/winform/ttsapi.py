

def openwin():
    from videotrans.configure.contants import LISTEN_TEXT
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,app_cfg, params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.util.help_misc import show_error
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        extra = winobj.extra.text().strip()
        role = winobj.voice_role.toPlainText().strip()

        params["ttsapi_url"] = url
        params["ttsapi_extra"] = extra
        params["ttsapi_voice_role"] = role
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('zh'),
            "role": winobj.voice_role.toPlainText().strip().split(',')[0].strip(),
            "filename": config.TEMP_DIR + f"/{time.time()}-ttsapi.wav",
            "tts_type": tts.TTS_API}],
                         language="zh",
                         tts_type=tts.TTS_API)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        extra = winobj.extra.text().strip()
        role = winobj.voice_role.toPlainText().strip().replace('\n', '')
        params["ttsapi_url"] = url
        params["ttsapi_extra"] = extra
        params["ttsapi_voice_role"] = role
        params.save()
        winobj.close()

    from videotrans.component.set_form import TtsapiForm
    winobj = TtsapiForm()
    app_cfg.child_forms['ttsapi'] = winobj
    if params["ttsapi_url"]:
        winobj.api_url.setText(str(params["ttsapi_url"]))
    if params["ttsapi_voice_role"]:
        winobj.voice_role.setPlainText(str(params["ttsapi_voice_role"]))
    if params["ttsapi_extra"]:
        winobj.extra.setText(str(params["ttsapi_extra"]))



    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
