

def openwin():
    from videotrans.configure.contants import LISTEN_TEXT
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import AzurettsForm

    winobj = AzurettsForm()
    app_cfg.child_forms['azuretts'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.speech_key.text().strip()
        if not key:
            show_error('填写Azure speech key ')
            return
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()
        params['azure_speech_key'] = key
        params['azure_speech_region'] = region
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text":  LISTEN_TEXT.get('zh'), "role": 'zh-CN-YunjianNeural',
                                                    "filename": config.TEMP_DIR + f"/{time.time()}-azure.wav",
                                                    "tts_type": tts.AZURE_TTS}], language="zh", tts_type=tts.AZURE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText('Testing...')

    def save():
        params['azure_speech_key'] = winobj.speech_key.text()
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()
        params['azure_speech_region'] = region
        params.save()
        winobj.close()

    if params.get('azure_speech_region','') and params.get('azure_speech_region','').startswith('http'):
        winobj.speech_region.setText(str(params.get('azure_speech_region','')))
    else:
        winobj.azuretts_area.setCurrentText(str(params.get('azure_speech_region','')))
    if params.get('azure_speech_key',''):
        winobj.speech_key.setText(str(params.get('azure_speech_key','')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
