def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,app_cfg, params
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

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()
        apiurl = winobj.apiurl.currentText()

        if not apikey:
            return tools.show_error(tr("SK is required"))


        emotion = winobj.emotion.currentText()
        params["minimaxi_emotion"] = emotion
        params["minimaxi_apikey"] = apikey
        params["minimaxi_model"] = model
        params["minimaxi_apiurl"] = apiurl
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "青涩青年音色" if "api.minimaxi.com"==apiurl else 'Reliable Executive',
            "filename": config.TEMP_DIR + f"/{time.time()}-minimaxi.wav",
            "tts_type": tts.MINIMAXI_TTS}],
                         language="zh",
                         tts_type=tts.MINIMAXI_TTS)
        wk.uito.connect(feed)
        wk.start()
        tools.set_process(text='', type="refreshtts")

    def save():

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()
        apiurl = winobj.apiurl.currentText()
        params["minimaxi_apiurl"] = apiurl



        emotion = winobj.emotion.currentText()
        params["minimaxi_emotion"] = emotion

        params["minimaxi_apikey"] = apikey
        params["minimaxi_model"] = model
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()


    from videotrans.component.set_form import MinimaxiForm
    winobj = MinimaxiForm()
    app_cfg.child_forms['minimaxi'] = winobj


    winobj.apikey.setText(str(params.get("minimaxi_apikey",'')))
    winobj.apiurl.setCurrentText(params.get("minimaxi_apiurl",'api.minimaxi.com'))

    winobj.emotion.setCurrentText(params.get("minimaxi_emotion",''))
    winobj.model.setCurrentText(params.get("minimaxi_model",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
