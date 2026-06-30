def openwin():
    from videotrans.configure.config import tr,app_cfg,settings,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.winform._helpers import make_setallmodels
    from videotrans.component.set_form import OpenAITTSForm

    winobj = OpenAITTSForm()
    app_cfg.child_forms['openaitts'] = winobj
    winobj.update_ui()

    def feed(d):
        if d.startswith("ok"):
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_openaitts.setText(tr("Test"))

    def test():
        params["openaitts_key"] = winobj.openaitts_key.text()
        params["openaitts_api"] = tools.process_openai_api(winobj.openaitts_api.text().strip())
        params["openaitts_model"] = winobj.openaitts_model.currentText()
        params["openaitts_instructions"] = winobj.openaitts_instructions.text()
        params.save()
        winobj.test_openaitts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        t = winobj.edit_roles.toPlainText().strip().replace('\uff0c', ',').rstrip(',').split(',')
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
            "role": 'alloy' if not t or not t[0].strip() else t[0].strip(),
            "filename": config.TEMP_DIR + f"/{time.time()}-openai.wav",
            "tts_type": tts.OPENAI_TTS}],
                         language="zh",
                         tts_type=tts.OPENAI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["openaitts_key"] = winobj.openaitts_key.text()
        params["openaitts_api"] = tools.process_openai_api(winobj.openaitts_api.text().strip())
        params["openaitts_model"] = winobj.openaitts_model.currentText()
        params["openaitts_instructions"] = winobj.openaitts_instructions.text()
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    def setedit_roles():
        params['openaitts_role'] = winobj.edit_roles.toPlainText().strip().replace('\uff0c', ',').rstrip(',')
        params.save()

    winobj.set_openaitts.clicked.connect(save)
    winobj.test_openaitts.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'openaitts_model', 'openaitts_model'))
    winobj.edit_roles.textChanged.connect(setedit_roles)
    winobj.show()
