def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.speech_key.text().strip()
        if not key:
            tools.show_error('填写Azure speech key ')
            return
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": 'zh-CN-YunjianNeural',
                                                    "filename": config.TEMP_HOME + f"/{time.time()}-azure.wav",
                                                    "tts_type": tts.AZURE_TTS}], language="zh", tts_type=tts.AZURE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText('Testing...')

    def save():
        key = winobj.speech_key.text()
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import AzurettsForm

    winobj = AzurettsForm()
    config.child_forms['azuretts'] = winobj
    if config.params.get('azure_speech_region','') and config.params.get('azure_speech_region','').startswith('http'):
        winobj.speech_region.setText(config.params.get('azure_speech_region',''))
    else:
        winobj.azuretts_area.setCurrentText(config.params.get('azure_speech_region',''))
    if config.params.get('azure_speech_key',''):
        winobj.speech_key.setText(config.params.get('azure_speech_key',''))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
