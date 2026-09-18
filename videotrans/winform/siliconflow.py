

def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.help_misc import show_error
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from pathlib import Path

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.guiji_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["guiji_key"] = key
        params["guiji_model"] = winobj.guiji_model.currentText()
        params["guiji_asr_model"] = winobj.guiji_asr_model.currentText()
        params["guiji_tts_model"] = winobj.guiji_tts_model.currentText()
        params["guiji_max_token"] = winobj.max_token.text().strip()
        params["guiji_thinking"] = winobj.guiji_thinking.isChecked()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.SILICONFLOW_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["guiji_key"] = winobj.guiji_key.text().strip()
        params["guiji_model"] = winobj.guiji_model.currentText()
        params["guiji_max_token"] = winobj.max_token.text().strip()
        params["guiji_thinking"] = winobj.guiji_thinking.isChecked()
        params["guiji_asr_model"] = winobj.guiji_asr_model.currentText()
        params["guiji_tts_model"] = winobj.guiji_tts_model.currentText()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'guiji_model', 'guiji_model'))
    winobj.test.clicked.connect(test)
    return winobj
