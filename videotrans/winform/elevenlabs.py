

def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr


    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

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
            import time
            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text": 'hello,my friend',
                "role": 'Aria',
                "filename": config.TEMP_HOME + f"/{time.time()}-elevenlabs.wav",
                "tts_type": tts.ELEVENLABS_TTS}],
                             language="en",
                             tts_type=tts.ELEVENLABS_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText(tr("Testing..."))
        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            tools.show_error(get_msg_from_except(e))

    from videotrans.component import ElevenlabsForm
    winobj = ElevenlabsForm()
    config.child_forms['elevenlabs'] = winobj
    winobj.elevenlabstts_key.setText(config.params.get('elevenlabstts_key',''))
    winobj.elevenlabstts_models.setCurrentText(config.params.get('elevenlabstts_models',''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
