def openwin():
    from videotrans.configure.config import tr,app_cfg,settings,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import ChatttsForm

    winobj = ChatttsForm()
    app_cfg.child_forms['chattts'] = winobj

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
        return url

    def test():
        params['chattts_api'] = _fix_url(winobj.chattts_address.text().strip())
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb', "role": "boy1",
                                                    "filename": config.TEMP_DIR + f"/{time.time()}-chattts.wav",
                                                    "tts_type": tts.CHATTTS}], language="zh", tts_type=tts.CHATTTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["chattts_api"] = _fix_url(winobj.chattts_address.text().strip()).rstrip('/').replace('/tts', '')
        params.save()
        settings['chattts_voice'] = winobj.chattts_voice.text().strip()
        settings.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    winobj.chattts_address.setText(params.get("chattts_api",''))
    winobj.chattts_voice.setText(str(settings.get("chattts_voice",'')))
    winobj.set_chattts.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
