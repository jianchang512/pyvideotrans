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
        key = winobj.cheaperinference_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["cheaperinference_key"] = key
        params["cheaperinference_model"] = winobj.cheaperinference_model.currentText()
        params["cheaperinference_max_token"] = winobj.max_token.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.CHEAPERINFERENCE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["cheaperinference_key"] = winobj.cheaperinference_key.text().strip()
        params["cheaperinference_model"] = winobj.cheaperinference_model.currentText()
        params["cheaperinference_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'cheaperinference_model', 'cheaperinference_model'))
    winobj.test.clicked.connect(test)
    return winobj
