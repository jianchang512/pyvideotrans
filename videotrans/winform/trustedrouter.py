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
        key = winobj.trustedrouter_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["trustedrouter_key"] = key
        params["trustedrouter_model"] = winobj.trustedrouter_model.currentText()
        params["trustedrouter_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TRUSTEDROUTER_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["trustedrouter_key"] = winobj.trustedrouter_key.text().strip()
        params["trustedrouter_model"] = winobj.trustedrouter_model.currentText()
        params["trustedrouter_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'trustedrouter_model', 'trustedrouter_model'))
    winobj.test.clicked.connect(test)
    return winobj
