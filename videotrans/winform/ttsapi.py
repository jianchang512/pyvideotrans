def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        extra = winobj.extra.text()
        role = winobj.voice_role.toPlainText().strip()
        language_boost = winobj.language_boost.currentText()

        params["ttsapi_language_boost"] = language_boost
        emotion = winobj.emotion.currentText()
        params["ttsapi_emotion"] = emotion
        params["ttsapi_url"] = url
        params["ttsapi_extra"] = extra
        params["ttsapi_voice_role"] = role
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": winobj.voice_role.toPlainText().strip().split(',')[0].strip(),
            "filename": TEMP_DIR + f"/{time.time()}-ttsapi.wav",
            "tts_type": tts.TTS_API}],
                         language="zh",
                         tts_type=tts.TTS_API)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        extra = winobj.extra.text()
        role = winobj.voice_role.toPlainText().strip().replace('\n', '')
        language_boost = winobj.language_boost.currentText()
        params["ttsapi_language_boost"] = language_boost

        emotion = winobj.emotion.currentText()
        params["ttsapi_emotion"] = emotion

        params["ttsapi_url"] = url
        params["ttsapi_extra"] = extra
        params["ttsapi_voice_role"] = role
        params.save()
        winobj.close()

    from videotrans.component.set_form import TtsapiForm
    winobj = TtsapiForm()
    app_cfg.child_forms['ttsapi'] = winobj
    if params["ttsapi_url"]:
        winobj.api_url.setText(params["ttsapi_url"])
    if params["ttsapi_voice_role"]:
        winobj.voice_role.setPlainText(params["ttsapi_voice_role"])
    if params["ttsapi_extra"]:
        winobj.extra.setText(params["ttsapi_extra"])

    if params["ttsapi_language_boost"]:
        winobj.language_boost.setCurrentText(params["ttsapi_language_boost"])
    if params["ttsapi_emotion"]:
        winobj.emotion.setCurrentText(params["ttsapi_emotion"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
