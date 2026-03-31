

def openwin():
    from PySide6 import QtWidgets
    import json
    from videotrans.configure.config import ROOT_DIR, tr, app_cfg, settings, params, TEMP_DIR, logger
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice

    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", tr("CAMB AI voices refreshed"))
        winobj.test.setText(tr("Test"))

    def save():
        key = winobj.camb_api_key.text()
        model = winobj.camb_speech_model.currentText()
        params['camb_api_key'] = key
        params['camb_speech_model'] = model
        params.save()
        winobj.close()

    def test():
        key = winobj.camb_api_key.text()
        params['camb_api_key'] = key

        try:
            from videotrans import tts
            from videotrans.task.simple_runnable_qt import run_in_threadpool
            from videotrans.util.help_role import get_camb_role
            import time

            voices = get_camb_role(force=True)
            if not voices or len(voices) < 2:
                tools.show_error("Failed to get CAMB AI voices. Check your API key.")
                return

            # Use first available voice for test
            test_role = voices[1] if len(voices) > 1 else voices[0]
            if test_role in ['No', 'clone']:
                test_role = voices[2] if len(voices) > 2 else voices[0]

            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text": 'hello, my friend',
                "role": test_role,
                "filename": TEMP_DIR + f"/{time.time()}-cambtts.wav",
                "tts_type": tts.CAMB_TTS}],
                             language="en",
                             tts_type=tts.CAMB_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText(tr("Testing..."))

        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            tools.show_error(get_msg_from_except(e))

    from videotrans.component.set_form import CambTTSForm
    winobj = CambTTSForm()
    app_cfg.child_forms['cambtts'] = winobj
    winobj.camb_api_key.setText(params.get('camb_api_key', ''))
    winobj.camb_speech_model.setCurrentText(params.get('camb_speech_model', 'mars-flash'))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
