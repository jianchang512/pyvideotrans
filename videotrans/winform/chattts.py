def openwin():
    import json

    from PySide6 import QtWidgets
    from videotrans.configure.config import tr

    from videotrans.configure import config
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
        config.params['chattts_api'] = url
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": "boy1",
                                                    "filename": config.TEMP_HOME + f"/{time.time()}-chattts.wav",
                                                    "tts_type": tts.CHATTTS}], language="zh", tts_type=tts.CHATTTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.chattts_address.text().strip()
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
    winobj = ChatttsForm()
    config.child_forms['chattts'] = winobj

    winobj.chattts_address.setText(config.params.get("chattts_api",''))
    winobj.chattts_voice.setText(config.settings.get("chattts_voice",''))
    winobj.set_chattts.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
