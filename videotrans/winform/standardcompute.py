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
        key = winobj.standardcompute_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["standardcompute_key"] = key
        params["standardcompute_model"] = winobj.standardcompute_model.currentText()
        params["standardcompute_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.STANDARDCOMPUTE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["standardcompute_key"] = winobj.standardcompute_key.text().strip()
        params["standardcompute_model"] = winobj.standardcompute_model.currentText()
        params["standardcompute_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'standardcompute_model', 'standardcompute_model'))
    winobj.test.clicked.connect(test)
    return winobj
