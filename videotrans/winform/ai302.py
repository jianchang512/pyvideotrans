

def openwin():
    from pathlib import Path
    from videotrans.winform import get_cls
    import webbrowser
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels


    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()
    feed = make_feed_translator(winobj, "test_ai302")

    def test():
        params["ai302_key"] = winobj.ai302_key.text().strip()
        params["ai302_model"] = winobj.ai302_model.currentText()
        params["ai302_model_recogn"] = winobj.ai302_model_recogn.currentText()
        winobj.test_ai302.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.AI302_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_ai302():
        params["ai302_key"] = winobj.ai302_key.text().strip()
        params["ai302_model"] = winobj.ai302_model.currentText()
        params["ai302_model_recogn"] = winobj.ai302_model_recogn.currentText()
        params.save()
        winobj.close()

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'ai302_model', 'ai302_models'))
    winobj.set_ai302.clicked.connect(save_ai302)
    winobj.test_ai302.clicked.connect(test)
    winobj.label_0.clicked.connect(lambda: webbrowser.open_new_tab("https://pyvideotrans.com/302ai"))
    return winobj
