def openwin():
    from PySide6 import QtWidgets


    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():

        url = winobj.chattts_address.text().strip()

        if not url.startswith('http'):
            url = 'http://' + url
        params['chattts_api'] = url
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": "boy1",
                                                    "filename": TEMP_DIR + f"/{time.time()}-chattts.wav",
                                                    "tts_type": tts.CHATTTS}], language="zh", tts_type=tts.CHATTTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.chattts_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.rstrip('/').replace('/tts', '')
        voice = winobj.chattts_voice.text().strip()
        params["chattts_api"] = url
        params.save()
        settings['chattts_voice'] = voice
        settings.save()

        tools.set_process(text='chattts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import ChatttsForm
    winobj = ChatttsForm()
    app_cfg.child_forms['chattts'] = winobj

    winobj.chattts_address.setText(params.get("chattts_api",''))
    winobj.chattts_voice.setText(str(settings.get("chattts_voice",'')))
    winobj.set_chattts.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
