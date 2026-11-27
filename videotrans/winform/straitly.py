def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import tr, params
    from videotrans.util.help_misc import show_error
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.straitly_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["straitly_key"] = key
        params["straitly_model"] = winobj.straitly_model.currentText()
        params["straitly_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.STRAITLY_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["straitly_key"] = winobj.straitly_key.text().strip()
        params["straitly_model"] = winobj.straitly_model.currentText()
        params["straitly_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'straitly_model', 'straitly_model'))
    winobj.test.clicked.connect(test)
    return winobj
