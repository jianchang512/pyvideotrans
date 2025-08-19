def openwin():
    import json

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():

        url = winobj.chattts_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['chattts_api'] = url
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": "boy1",
                                                    "filename": config.TEMP_HOME + f"/test-chattts.wav",
                                                    "tts_type": tts.CHATTTS}], language="zh", tts_type=tts.CHATTTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.chattts_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.rstrip('/').replace('/tts', '')
        voice = winobj.chattts_voice.text().strip()
        config.params["chattts_api"] = url
        config.getset_params(config.params)
        config.settings['chattts_voice'] = voice
        with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

        tools.set_process(text='chattts', type="refreshtts")
        winobj.close()

    from videotrans.component import ChatttsForm
    winobj = config.child_forms.get('chatttsw')
    if winobj is not None:
        config.settings = config.parse_init()
        if config.settings["chattts_voice"]:
            winobj.chattts_voice.setText(config.settings["chattts_voice"])
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatttsForm()
    config.child_forms['chatttsw'] = winobj

    if config.params["chattts_api"]:
        winobj.chattts_address.setText(config.params["chattts_api"])
    if config.settings["chattts_voice"]:
        winobj.chattts_voice.setText(config.settings["chattts_voice"])
    winobj.set_chattts.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
