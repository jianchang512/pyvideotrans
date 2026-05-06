
def openwin():
    from pathlib import Path
    from PySide6 import QtWidgets
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            tools.set_process(text='chatterbox', type="refreshtts")
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():
        url = winobj.api_url.text().strip()

        if not url.startswith('http'):
            url = 'http://' + url
        params["chatterbox_url"] = url
        params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)
        params.save()
        
        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_audio')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))
        
    
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": 'Hello,my friend,welcom to China', 
            "role": rolename,
            "filename": TEMP_DIR + f"/test-chatterbox.wav",
            "tts_type": tts.CHATTERBOX_TTS}], language="en",
            tts_type=tts.CHATTERBOX_TTS)
        wk.uito.connect(feed)
        wk.start()


    def save():
        url = winobj.api_url.text().strip()

        if not url.startswith('http'):
            url = 'http://' + url


        params["chatterbox_url"] = url

        params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)

        params.save()
        tools.set_process(text='chatterbox', type="refreshtts")

        winobj.close()

    from videotrans.component.set_form import ChatterboxForm
    winobj = ChatterboxForm()
    app_cfg.child_forms['chatterbox'] = winobj
    winobj.api_url.setText(params.get("chatterbox_url",''))
    winobj.cfg_weight.setText(str(params.get("chatterbox_cfg_weight",'')))
    winobj.exaggeration.setText(str(params.get("chatterbox_exaggeration",'')))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
