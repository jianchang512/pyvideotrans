

def openwin():
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr, params, app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import LiteLLMForm

    winobj = LiteLLMForm()
    app_cfg.child_forms['litellm'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.litellm_key.text()
        params["litellm_api"] = winobj.litellm_api.text().strip()
        params["litellm_key"] = key
        params["litellm_model"] = winobj.litellm_model.currentText()
        params["litellm_max_token"] = winobj.max_token.text().strip()
        params["litellm_reasoning_effort"] = winobj.reasoning_effort.currentText()
        winobj.test.setText(tr("Testing..."))
        params.save()
        task = TestSrtTrans(parent=winobj, translator_type=translator.LITELLM_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["litellm_api"] = winobj.litellm_api.text().strip()
        params["litellm_key"] = winobj.litellm_key.text()
        params["litellm_model"] = winobj.litellm_model.currentText()
        params["litellm_max_token"] = winobj.max_token.text().strip()
        params["litellm_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'litellm_model', 'litellm_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
