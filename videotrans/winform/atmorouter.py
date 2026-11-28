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
        key = winobj.atmorouter_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["atmorouter_key"] = key
        params["atmorouter_model"] = winobj.atmorouter_model.currentText()
        params["atmorouter_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.ATMOROUTER_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["atmorouter_key"] = winobj.atmorouter_key.text().strip()
        params["atmorouter_model"] = winobj.atmorouter_model.currentText()
        params["atmorouter_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'atmorouter_model', 'atmorouter_model'))
    winobj.test.clicked.connect(test)
    return winobj
