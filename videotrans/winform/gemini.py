def openwin():
    import os
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import GeminiForm

    winobj = GeminiForm()
    app_cfg.child_forms['gemini'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.gemini_key.text()
        os.environ['GOOGLE_API_KEY'] = key
        params["gemini_key"] = key
        params["gemini_model"] = winobj.model.currentText()
        params["gemini_maxtoken"] = winobj.gemini_maxtoken.text()
        params["gemini_ttsmodel"] = winobj.ttsmodel.currentText()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.GEMINI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["gemini_key"] = winobj.gemini_key.text()
        params["gemini_model"] = winobj.model.currentText()
        params["gemini_maxtoken"] = winobj.gemini_maxtoken.text()
        params["gemini_ttsmodel"] = winobj.ttsmodel.currentText()
        params.save()
        winobj.close()

    winobj.set_gemini.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'model', 'gemini_model'))
    winobj.show()
