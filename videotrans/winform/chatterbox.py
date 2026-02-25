
def openwin():
    from pathlib import Path
    from PySide6 import QtWidgets
    from videotrans.configure import config
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
        params["chatterbox_role"] = winobj.role.toPlainText().strip()
        params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)

        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": 'Hello,my friend,welcom to China', "role": getrole(),
                                                    "filename": TEMP_DIR + f"/test-chatterbox.wav",
                                                    "tts_type": tts.CHATTERBOX_TTS}], language="en",
                         tts_type=tts.CHATTERBOX_TTS)
        wk.uito.connect(feed)
        wk.start()
        params.save()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip()
            if not Path(ROOT_DIR + f"/chatterbox/{s}").exists():
                tools.show_error(tr('Please make sure that the audio file {} exists in the chatterbox folder',s))
                return

            role = s

        return role

    def save():
        url = winobj.api_url.text().strip()

        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()

        params["chatterbox_url"] = url
        params["chatterbox_role"] = role

        params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)

        params.save()
        tools.set_process(text='chatterbox', type="refreshtts")

        winobj.close()

    from videotrans.component.set_form import ChatterboxForm
    winobj = ChatterboxForm()
    app_cfg.child_forms['chatterbox'] = winobj
    winobj.api_url.setText(params.get("chatterbox_url",''))
    winobj.role.setPlainText(params.get("chatterbox_role",''))
    winobj.cfg_weight.setText(str(params.get("chatterbox_cfg_weight",'')))
    winobj.exaggeration.setText(str(params.get("chatterbox_exaggeration",'')))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
