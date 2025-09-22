def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText('测试api' if config.defaulelang == 'zh' else 'Test api')

    def test():

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()

        if not apikey:
            return tools.show_error("必须填写密钥" if config.defaulelang=='zh' else 'SK is required')


        emotion = winobj.emotion.currentText()
        config.params["minimaxi_emotion"] = emotion
        config.params["minimaxi_apikey"] = apikey
        config.params["minimaxi_model"] = model
        config.getset_params(config.params)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "青涩青年音色",
            "filename": config.TEMP_HOME + f"/{time.time()}-minimaxi.wav",
            "tts_type": tts.MINIMAXI_TTS}],
                         language="zh",
                         tts_type=tts.MINIMAXI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()



        emotion = winobj.emotion.currentText()
        config.params["minimaxi_emotion"] = emotion

        config.params["minimaxi_apikey"] = apikey
        config.params["minimaxi_model"] = model
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import MinimaxiForm
    winobj = config.child_forms.get('minimaxiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = MinimaxiForm()
    config.child_forms['minimaxiw'] = winobj


    if config.params["minimaxi_apikey"]:
        winobj.apikey.setText(config.params["minimaxi_apikey"])

    if config.params["minimaxi_emotion"]:
        winobj.emotion.setCurrentText(config.params["minimaxi_emotion"])
    if config.params["minimaxi_model"]:
        winobj.emotion.setCurrentText(config.params["minimaxi_model"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
