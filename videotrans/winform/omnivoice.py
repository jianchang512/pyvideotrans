def openwin():
    from PySide6 import QtWidgets
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        
        role = winobj.role.toPlainText().strip()
        if not role:
            return tools.show_error(tr('"The reference audio path name and the text corresponding to the reference audio must be filled in the settings"'))
        
        params["omnivoice_url"] = url

        params["omnivoice_role"] = role
        
        params.save()
        
        for it in role.split("\n"):
            file=it.split('#')[0]
            file=ROOT_DIR+f'/f5-tts/{file}'
            if not Path(file).exists():
                return tools.show_error(tr("No reference audio {} exists",file))
            if not file.endswith('.wav'):
                return tools.show_error(tr('Please upload reference audio in wav format'))

        
        
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友,希望你的每一天都美好愉快',
            "role": role.split("\n")[0].split('#')[0],
            "filename": TEMP_DIR + f"/{time.time()}-omnivoice.wav",
            "tts_type": tts.OMNIVOICE_TTS}],
                         language="Auto",
                         tts_type=tts.OMNIVOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()
        if not role:
            return tools.show_error(tr("Please upload reference audio in wav format"))

        params["omnivoice_url"] = url

        params["omnivoice_role"] = role
        params.save()
        tools.set_process(text='omnivoice', type="refreshtts")

        winobj.close()

    from videotrans.component.set_form import OmniVoiceForm
    winobj = OmniVoiceForm()
    app_cfg.child_forms['omnivoice'] = winobj
    if params["omnivoice_url"]:
        winobj.api_url.setText(params["omnivoice_url"])
    if params["omnivoice_role"]:
        winobj.role.setPlainText(params["omnivoice_role"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
