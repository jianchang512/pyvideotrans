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
        key = winobj.cloudgpu_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["cloudgpu_key"] = key
        params["cloudgpu_model"] = winobj.cloudgpu_model.currentText()
        params["cloudgpu_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.CLOUDGPU_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["cloudgpu_key"] = winobj.cloudgpu_key.text().strip()
        params["cloudgpu_model"] = winobj.cloudgpu_model.currentText()
        params["cloudgpu_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'cloudgpu_model', 'cloudgpu_model'))
    winobj.test.clicked.connect(test)
    return winobj
