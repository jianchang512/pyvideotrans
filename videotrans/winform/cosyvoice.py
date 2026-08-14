

def openwin():
    from videotrans.configure.contants import LISTEN_TEXT
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.util.help_role import get_f5tts_role
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import CosyVoiceForm

    winobj = CosyVoiceForm()
    app_cfg.child_forms['cosyvoice'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr('Test'))

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["cosyvoice_url"] = _fix_url(winobj.api_url.text().strip())
        params["cosyvoice_instruct_text"] = winobj.instruct_text.text()
        params.save()
        _rolename = next(reversed(get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return show_error(tr("No reference audio {} exists",file))
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('zh'),
            "role": rolename,
            "filename": config.TEMP_DIR + f"/{time.time()}-cosyvoice.wav",
            "tts_type": tts.COSYVOICE_TTS}],
                         language="zh",
                         tts_type=tts.COSYVOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["cosyvoice_url"] = _fix_url(winobj.api_url.text().strip())
        params["cosyvoice_instruct_text"] = winobj.instruct_text.text()
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()

    if params["cosyvoice_url"]:
        winobj.api_url.setText(str(params["cosyvoice_url"]))
    if params.get("cosyvoice_instruct_text"):
        winobj.instruct_text.setText(str(params.get("cosyvoice_instruct_text")))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
