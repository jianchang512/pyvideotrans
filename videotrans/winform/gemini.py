def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels


    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.gemini_key.text().strip()
        params["gemini_key"] = key
        params["gemini_model"] = winobj.model.currentText()
        params["gemini_maxtoken"] = winobj.gemini_maxtoken.text()
        params["gemini_ttsmodel"] = winobj.ttsmodel.currentText()
        params["gemini_asrmodel"] = winobj.asrmodel.currentText()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.GEMINI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["gemini_key"] = winobj.gemini_key.text().strip()
        params["gemini_model"] = winobj.model.currentText()
        params["gemini_maxtoken"] = winobj.gemini_maxtoken.text()
        params["gemini_ttsmodel"] = winobj.ttsmodel.currentText()
        params["gemini_asrmodel"] = winobj.asrmodel.currentText()
        params.save()
        winobj.close()

    winobj.set_gemini.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'model', 'gemini_model'))
    return winobj
