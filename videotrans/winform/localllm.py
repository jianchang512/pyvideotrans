def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import LocalLLMForm

    winobj = LocalLLMForm()
    app_cfg.child_forms['localllm'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test_localllm")

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["localllm_key"] = winobj.localllm_key.text()
        params["localllm_api"] = _fix_url(winobj.localllm_api.text().strip())
        params["localllm_max_token"] = winobj.localllm_max_token.text().strip()
        params["localllm_model"] = winobj.localllm_model.currentText()
        winobj.test_localllm.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.LOCALLLM_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_localllm():
        params["localllm_key"] = winobj.localllm_key.text()
        params["localllm_api"] = _fix_url(winobj.localllm_api.text().strip())
        params["localllm_max_token"] = winobj.localllm_max_token.text().strip()
        params["localllm_model"] = winobj.localllm_model.currentText()
        params.save()
        winobj.close()

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'localllm_model', 'localllm_model'))
    winobj.set_localllm.clicked.connect(save_localllm)
    winobj.test_localllm.clicked.connect(test)
    winobj.show()
