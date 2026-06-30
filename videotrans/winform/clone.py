def openwin():
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import CloneForm

    winobj = CloneForm()
    app_cfg.child_forms['clone'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url.rstrip('/')

    def test():
        params['clone_api'] = _fix_url(winobj.clone_address.text().strip())
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
            "role": params.get("clone_voicelist",'')[1] if len(params.get("clone_voicelist",'')) > 1 else '',
            "filename": config.TEMP_DIR + f"/{time.time()}-clonevoice.wav",
            "tts_type": tts.CLONE_VOICE_TTS}],
                         language="zh",
                         tts_type=tts.CLONE_VOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["clone_api"] = _fix_url(winobj.clone_address.text().strip())
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    if params.get("clone_api",''):
        winobj.clone_address.setText(params.get("clone_api",''))
    winobj.set_clone.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
