def openwin():
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import FishTTSForm

    winobj = FishTTSForm()
    app_cfg.child_forms['fishtts'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "Ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["fishtts_url"] = _fix_url(winobj.api_url.text().strip())
        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))
        winobj.test.setText('\u6d4b\u8bd5\u4e2d\u8bf7\u7a0d\u7b49...')
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
            "role": rolename,
            "filename": config.TEMP_DIR + f"/{time.time()}-fishtts.wav",
            "tts_type": tts.FISHTTS}],
                         language="zh",
                         tts_type=tts.FISHTTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["fishtts_url"] = _fix_url(winobj.api_url.text().strip())
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    winobj.api_url.setText(params.get("fishtts_url",''))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
