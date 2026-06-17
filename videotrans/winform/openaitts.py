def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,app_cfg,settings,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_openaitts.setText(tr("Test"))

    def test():
        key = winobj.openaitts_key.text()
        url = tools.process_openai_api(winobj.openaitts_api.text().strip())
        model = winobj.openaitts_model.currentText()
        intru = winobj.openaitts_instructions.text()
        params["openaitts_instructions"] = intru

        params["openaitts_key"] = key
        params["openaitts_api"] = url
        params["openaitts_model"] = model
        params.save()
        winobj.test_openaitts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        t = winobj.edit_roles.toPlainText().strip().replace('，', ',').rstrip(',').split(',')
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": 'alloy' if not t or not t[0].strip() else t[0].strip(),
            "filename": config.TEMP_DIR + f"/{time.time()}-openai.wav",
            "tts_type": tts.OPENAI_TTS}],
                         language="zh",
                         tts_type=tts.OPENAI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        key = winobj.openaitts_key.text()
        url = tools.process_openai_api(winobj.openaitts_api.text().strip())

        model = winobj.openaitts_model.currentText()
        intru = winobj.openaitts_instructions.text()
        params["openaitts_instructions"] = intru

        params["openaitts_key"] = key
        params["openaitts_api"] = url
        params["openaitts_model"] = model
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.openaitts_model.currentText()
        winobj.openaitts_model.clear()
        winobj.openaitts_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.openaitts_model.setCurrentText(current_text)
        settings['openaitts_model'] = t
        settings.save()

    def setedit_roles():
        t = winobj.edit_roles.toPlainText().strip().replace('，', ',').rstrip(',')
        params['openaitts_role'] = t
        params.save()



    from videotrans.component.set_form import OpenAITTSForm
    winobj = OpenAITTSForm()
    app_cfg.child_forms['openaitts'] = winobj
    winobj.update_ui()

    winobj.set_openaitts.clicked.connect(save)
    winobj.test_openaitts.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.edit_roles.textChanged.connect(setedit_roles)
    winobj.show()
