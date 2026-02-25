

def openwin():
    from PySide6 import QtWidgets
    import json

    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", tr("elevenlabs toggle role"))
        winobj.test.setText(tr("Test"))

    def save():
        key = winobj.elevenlabstts_key.text()
        model = winobj.elevenlabstts_models.currentText()
        params['elevenlabstts_key'] = key
        params['elevenlabstts_models'] = model
        params.save()
        winobj.close()

    def test():
        key = winobj.elevenlabstts_key.text()
        params['elevenlabstts_key'] = key

        try:
            from videotrans import tts
            from videotrans.task.simple_runnable_qt import run_in_threadpool     

            import time
            with open(ROOT_DIR+'/videotrans/voicejson/elevenlabs.json','r',encoding='utf-8') as f:
                jsondata=json.loads(f.read())
            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text": 'hello,my friend',
                "role": list(jsondata.keys())[0],
                "filename": TEMP_DIR + f"/{time.time()}-elevenlabs.wav",
                "tts_type": tts.ELEVENLABS_TTS}],
                             language="en",
                             tts_type=tts.ELEVENLABS_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText(tr("Testing..."))
            
            run_in_threadpool(tools.get_elevenlabs_role,True)
            
        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            tools.show_error(get_msg_from_except(e))

    from videotrans.component.set_form import ElevenlabsForm
    winobj = ElevenlabsForm()
    app_cfg.child_forms['elevenlabs'] = winobj
    winobj.elevenlabstts_key.setText(params.get('elevenlabstts_key',''))
    winobj.elevenlabstts_models.setCurrentText(params.get('elevenlabstts_models',''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
