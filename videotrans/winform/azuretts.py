def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.speech_key.text().strip()
        if not key:
            tools.show_error('填写Azure speech key ', False)
            return
        region = winobj.speech_region.text().strip()
        if not region or not region.startswith('https:'):
            region = winobj.azuretts_area.currentText()

        config.params['azure_speech_key'] = key
        config.params['azure_speech_region'] = region
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": 'zh-CN-YunjianNeural',
                                                    "filename": config.TEMP_HOME + f"/test-azure.wav",
                                                    "tts_type": tts.AZURE_TTS}], language="zh", tts_type=tts.AZURE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText('testing...')

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
    winobj = config.child_forms.get('azurettsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AzurettsForm()
    config.child_forms['azurettsw'] = winobj
    if config.params['azure_speech_region'] and config.params['azure_speech_region'].startswith('http'):
        winobj.speech_region.setText(config.params['azure_speech_region'])
    else:
        winobj.azuretts_area.setCurrentText(config.params['azure_speech_region'])
    if config.params['azure_speech_key']:
        winobj.speech_key.setText(config.params['azure_speech_key'])
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
