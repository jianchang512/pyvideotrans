

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
        key = winobj.siliconflow_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["siliconflow_key"] = key
        params["siliconflow_model"] = winobj.siliconflow_model.currentText()
        params["siliconflow_tts_model"] = winobj.siliconflow_tts_model.currentText()
        params["siliconflow_max_token"] = winobj.max_token.text().strip()
        params["siliconflow_thinking"] = winobj.siliconflow_thinking.isChecked()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.SILICONFLOW_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["siliconflow_key"] = winobj.siliconflow_key.text().strip()
        params["siliconflow_model"] = winobj.siliconflow_model.currentText()
        params["siliconflow_max_token"] = winobj.max_token.text().strip()
        params["siliconflow_thinking"] = winobj.siliconflow_thinking.isChecked()
        params["siliconflow_tts_model"] = winobj.siliconflow_tts_model.currentText()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'siliconflow_model', 'siliconflow_model'))
    winobj.test.clicked.connect(test)
    return winobj
