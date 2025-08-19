def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        winobj.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
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
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": winobj.voice_role.toPlainText().strip().split(',')[0].strip(),
            "filename": config.TEMP_HOME + f"/test-ttsapi.wav",
            "tts_type": tts.TTS_API}],
                         language="zh",
                         tts_type=tts.TTS_API)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
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

    from videotrans.component import TtsapiForm
    winobj = config.child_forms.get('ttsapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = TtsapiForm()
    config.child_forms['ttsapiw'] = winobj
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
