

def openwin():
    from videotrans.configure.contants import LISTEN_TEXT
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import MinimaxiForm

    winobj = MinimaxiForm()
    app_cfg.child_forms['minimaxi'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        apikey = winobj.apikey.text().strip()
        model = winobj.model.currentText()
        apiurl = winobj.apiurl.currentText()
        if not apikey:
            return show_error(tr("SK is required"))
        params["minimaxi_apikey"] = apikey
        params["minimaxi_model"] = model
        params["minimaxi_apiurl"] = apiurl
        params["minimaxi_emotion"] = winobj.emotion.currentText()
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('zh'),
            "role": "\u9752\u6da9\u9752\u5e74\u97f3\u8272" if "api.minimaxi.com"==apiurl else 'Reliable Executive',
            "filename": config.TEMP_DIR + f"/{time.time()}-minimaxi.wav",
            "tts_type": tts.MINIMAXI_TTS}],
                         language="zh",
                         tts_type=tts.MINIMAXI_TTS)
        wk.uito.connect(feed)
        wk.start()
        set_process(text='', type="refreshtts")

    def save():
        params["minimaxi_apikey"] = winobj.apikey.text().strip()
        params["minimaxi_model"] = winobj.model.currentText()
        params["minimaxi_apiurl"] = winobj.apiurl.currentText()
        params["minimaxi_emotion"] = winobj.emotion.currentText()
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()

    winobj.apikey.setText(str(params.get("minimaxi_apikey",'')))
    winobj.apiurl.setCurrentText(str(params.get("minimaxi_apiurl",'api.minimaxi.com')))
    winobj.emotion.setCurrentText(str(params.get("minimaxi_emotion",'')))
    winobj.model.setCurrentText(str(params.get("minimaxi_model",'')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
