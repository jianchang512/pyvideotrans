

def openwin():
    from pathlib import Path
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform import get_cls
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure.config import tr,app_cfg,params


    winobj = get_cls(Path(__file__).stem)()

    def feed(d):
        if d and d.startswith('ok'):
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        apikey = winobj.apikey.text().strip()
        apiurl = winobj.apiurl.currentText()
        if not apikey:
            return show_error(tr("SK is required"))
        params["minimaxi_apikey"] = apikey
        params["minimaxi_apiurl"] = apiurl
        params["minimaxi_tts_model"] = winobj.tts_model.currentText()
        params["minimaxi_emotion"] = winobj.emotion.currentText()
        params["minimaxi_text_model"] = winobj.text_model.currentText()
        params["minimaxi_asr_model"] = winobj.asr_model.currentText()
        params["minimaxi_max_token"] = winobj.max_token.text()
        params["minimaxi_thinking"] = winobj.minimaxi_thinking.isChecked()
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.MINIMAX_INDEX)
        task.uito.connect(feed)
        task.start()
        set_process(text='', type="refreshtts")

    def save():
        params["minimaxi_apikey"] = winobj.apikey.text().strip()
        params["minimaxi_apiurl"] = winobj.apiurl.currentText()
        params["minimaxi_tts_model"] = winobj.tts_model.currentText()
        params["minimaxi_emotion"] = winobj.emotion.currentText()
        params["minimaxi_text_model"] = winobj.text_model.currentText()
        params["minimaxi_asr_model"] = winobj.asr_model.currentText()
        params["minimaxi_max_token"] = winobj.max_token.text()
        params["minimaxi_thinking"] = winobj.minimaxi_thinking.isChecked()
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()


    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
