def openwin():
    import json
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_openaitts.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.openaitts_key.text()
        url = winobj.openaitts_api.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if tools.check_local_api(url) is not True:
            return

        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.openaitts_model.currentText()
        intru = winobj.openaitts_instructions.text()
        config.params["openaitts_instructions"] = intru

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = url
        config.params["openaitts_model"] = model
        config.getset_params(config.params)
        winobj.test_openaitts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": 'alloy',
            "filename": config.TEMP_HOME + f"/test-openai.wav",
            "tts_type": tts.OPENAI_TTS}],
                         language="zh",
                         tts_type=tts.OPENAI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save_openaitts():
        key = winobj.openaitts_key.text()
        url = winobj.openaitts_api.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        model = winobj.openaitts_model.currentText()
        intru = winobj.openaitts_instructions.text()
        config.params["openaitts_instructions"] = intru

        config.params["openaitts_key"] = key
        config.params["openaitts_api"] = url
        config.params["openaitts_model"] = model
        config.getset_params(config.params)
        tools.set_process(text='openaitts', type="refreshtts")
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.openaitts_model.currentText()
        winobj.openaitts_model.clear()
        winobj.openaitts_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.openaitts_model.setCurrentText(current_text)
        config.settings['openaitts_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def setedit_roles():
        t = winobj.edit_roles.toPlainText().strip().replace('，', ',').rstrip(',')
        config.params['openaitts_role'] = t
        config.getset_params(config.params)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['openaitts_model']
        allmodels = config.settings['openaitts_model'].split(',')

        winobj.openaitts_model.clear()
        winobj.openaitts_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)
        winobj.edit_roles.setPlainText(config.params['openaitts_role'])

        if config.params["openaitts_key"]:
            winobj.openaitts_key.setText(config.params["openaitts_key"])
        if config.params["openaitts_instructions"]:
            winobj.openaitts_instructions.setText(config.params.get("openaitts_instructions", ''))
        if config.params["openaitts_api"]:
            winobj.openaitts_api.setText(config.params["openaitts_api"])
        if config.params["openaitts_model"] and config.params['openaitts_model'] in allmodels:
            winobj.openaitts_model.setCurrentText(config.params["openaitts_model"])

    from videotrans.component import OpenAITTSForm
    winobj = config.child_forms.get('openaittsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = OpenAITTSForm()
    config.child_forms['openaittsw'] = winobj
    update_ui()

    winobj.set_openaitts.clicked.connect(save_openaitts)
    winobj.test_openaitts.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.edit_roles.textChanged.connect(setedit_roles)
    winobj.show()
