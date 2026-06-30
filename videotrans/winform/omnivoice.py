def openwin():
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import OmniVoiceForm

    winobj = OmniVoiceForm()
    app_cfg.child_forms['omnivoice'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["omnivoice_url"] = _fix_url(winobj.api_url.text().strip())
        params.save()
        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename, dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename = _rolename.get('ref_wav')
        file = ROOT_DIR + f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists", file))
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb,\u5e0c\u671b\u4f60\u7684\u6bcf\u4e00\u5929\u90fd\u7f8e\u597d\u6109\u5feb',
            "role":rolename,
            "filename": config.TEMP_DIR + f"/{time.time()}-omnivoice.wav",
            "tts_type": tts.OMNIVOICE_TTS}],
                         language="zh",
                         tts_type=tts.OMNIVOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["omnivoice_url"] = _fix_url(winobj.api_url.text().strip())
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    if params["omnivoice_url"]:
        winobj.api_url.setText(params["omnivoice_url"])
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
