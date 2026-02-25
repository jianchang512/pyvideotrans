def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
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

        params['azure_speech_key'] = key
        params['azure_speech_region'] = region
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": 'zh-CN-YunjianNeural',
                                                    "filename": TEMP_DIR + f"/{time.time()}-azure.wav",
                                                    "tts_type": tts.AZURE_TTS}], language="zh", tts_type=tts.AZURE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText('Testing...')

    def save():
        key = winobj.speech_key.text()
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        params['azure_speech_key'] = key
        params['azure_speech_region'] = region
        params.save()
        winobj.close()

    from videotrans.component.set_form import AzurettsForm

    winobj = AzurettsForm()
    app_cfg.child_forms['azuretts'] = winobj
    if params.get('azure_speech_region','') and params.get('azure_speech_region','').startswith('http'):
        winobj.speech_region.setText(params.get('azure_speech_region',''))
    else:
        winobj.azuretts_area.setCurrentText(params.get('azure_speech_region',''))
    if params.get('azure_speech_key',''):
        winobj.speech_key.setText(params.get('azure_speech_key',''))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
