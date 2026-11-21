def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import tr, params, app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        params["openllm_api"] = winobj.openllm_api.text().strip()
        params["openllm_key"] = winobj.openllm_key.text().strip()
        params["openllm_model"] = winobj.openllm_model.currentText()
        params["openllm_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.OPENLLM_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["openllm_api"] = winobj.openllm_api.text().strip()
        params["openllm_key"] = winobj.openllm_key.text().strip()
        params["openllm_model"] = winobj.openllm_model.currentText()
        params["openllm_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'openllm_model', 'openllm_model'))
    winobj.test.clicked.connect(test)
    return winobj
