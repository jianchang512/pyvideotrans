def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def save():
        key = winobj.elevenlabstts_key.text()
        model = winobj.elevenlabstts_models.currentText()
        config.params['elevenlabstts_key'] = key
        config.params['elevenlabstts_models'] = model
        config.getset_params(config.params)
        winobj.close()

    def test():
        key = winobj.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key

        try:
            from videotrans import tts
            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text": 'hello,my friend',
                "role": 'Aria',
                "filename": config.TEMP_HOME + f"/test-elevenlabs.wav",
                "tts_type": tts.ELEVENLABS_TTS}],
                             language="en",
                             tts_type=tts.ELEVENLABS_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

        except Exception as e:
            tools.show_error(str(e))

    from videotrans.component import ElevenlabsForm
    winobj = config.child_forms.get('elevenlabsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ElevenlabsForm()
    config.child_forms['elevenlabsw'] = winobj
    if config.params['elevenlabstts_key']:
        winobj.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
    if config.params['elevenlabstts_models']:
        winobj.elevenlabstts_models.setCurrentText(config.params['elevenlabstts_models'])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
