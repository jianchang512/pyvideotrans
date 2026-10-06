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
        key = winobj.atlascloud_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["atlascloud_key"] = key
        params["atlascloud_model"] = winobj.atlascloud_model.currentText()
        params["atlascloud_max_token"] = winobj.max_token.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.ATLASCLOUD_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["atlascloud_key"] = winobj.atlascloud_key.text().strip()
        params["atlascloud_model"] = winobj.atlascloud_model.currentText()
        params["atlascloud_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'atlascloud_model', 'atlascloud_model'))
    winobj.test.clicked.connect(test)
    return winobj
