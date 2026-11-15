def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import tr, params, app_cfg
    from videotrans.util.help_misc import show_error
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.requesty_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["requesty_key"] = key
        params["requesty_model"] = winobj.requesty_model.currentText()
        params["requesty_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.REQUESTY_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["requesty_key"] = winobj.requesty_key.text().strip()
        params["requesty_model"] = winobj.requesty_model.currentText()
        params["requesty_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'requesty_model', 'requesty_model'))
    winobj.test.clicked.connect(test)
    return winobj
