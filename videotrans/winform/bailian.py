

def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels


    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.bailian_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["bailian_key"] = key
        params["bailian_spaceid"] = winobj.bailian_spaceid.text().strip()
        params["bailian_model"] = winobj.bailian_model.currentText()
        params["bailian_ttsmodel"] = winobj.bailian_ttsmodel.currentText()
        params["bailian_domains"] = winobj.bailian_domains.text()
        params["bailian_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.BAILIAN_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["bailian_key"] = winobj.bailian_key.text().strip()
        params["bailian_spaceid"] = winobj.bailian_spaceid.text().strip()
        params["bailian_model"] = winobj.bailian_model.currentText()
        params["bailian_ttsmodel"] = winobj.bailian_ttsmodel.currentText()
        params["bailian_domains"] = winobj.bailian_domains.text()
        params["bailian_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'bailian_model', 'bailian_model'))
    winobj.test.clicked.connect(test)
    return winobj
