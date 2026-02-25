def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.clone_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params['clone_api'] = url
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": params.get("clone_voicelist",'')[1] if len(params.get("clone_voicelist",'')) > 1 else '',
            "filename": TEMP_DIR + f"/{time.time()}-clonevoice.wav",
            "tts_type": tts.CLONE_VOICE_TTS}],
                         language="zh",
                         tts_type=tts.CLONE_VOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.clone_address.text().strip()
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        params["clone_api"] = url
        params.save()
        tools.set_process(text='clone', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import CloneForm
    winobj = CloneForm()
    app_cfg.child_forms['clone'] = winobj
    if params.get("clone_api",''):
        winobj.clone_address.setText(params.get("clone_api",''))
    winobj.set_clone.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
