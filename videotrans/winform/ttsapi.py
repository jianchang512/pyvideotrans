from videotrans.configure.config import tr


def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config

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

        config.params["ttsapi_language_boost"] = language_boost
        emotion = winobj.emotion.currentText()
        config.params["ttsapi_emotion"] = emotion
        config.params["ttsapi_url"] = url
        config.params["ttsapi_extra"] = extra
        config.params["ttsapi_voice_role"] = role
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": winobj.voice_role.toPlainText().strip().split(',')[0].strip(),
            "filename": config.TEMP_HOME + f"/{time.time()}-ttsapi.wav",
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
        config.params["ttsapi_language_boost"] = language_boost

        emotion = winobj.emotion.currentText()
        config.params["ttsapi_emotion"] = emotion

        config.params["ttsapi_url"] = url
        config.params["ttsapi_extra"] = extra
        config.params["ttsapi_voice_role"] = role
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component.set_form import TtsapiForm
    winobj = TtsapiForm()
    config.child_forms['ttsapi'] = winobj
    if config.params["ttsapi_url"]:
        winobj.api_url.setText(config.params["ttsapi_url"])
    if config.params["ttsapi_voice_role"]:
        winobj.voice_role.setPlainText(config.params["ttsapi_voice_role"])
    if config.params["ttsapi_extra"]:
        winobj.extra.setText(config.params["ttsapi_extra"])

    if config.params["ttsapi_language_boost"]:
        winobj.language_boost.setCurrentText(config.params["ttsapi_language_boost"])
    if config.params["ttsapi_emotion"]:
        winobj.emotion.setCurrentText(config.params["ttsapi_emotion"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
