def openwin():
    import os
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import ChatgptForm

    winobj = ChatgptForm()
    app_cfg.child_forms['chatgpt'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test_chatgpt")

    def test():
        key = winobj.chatgpt_key.text()
        url = tools.process_openai_api(winobj.chatgpt_api.text().strip())
        params["chatgpt_key"] = key
        params["chatgpt_api"] = url
        params["chatgpt_max_token"] = winobj.chatgpt_max_token.text().strip()
        params["chatgpt_model"] = winobj.chatgpt_model.currentText()
        params["chatgpt_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        os.environ['OPENAI_API_KEY'] = key
        winobj.test_chatgpt.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.CHATGPT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_chatgpt():
        params["chatgpt_max_token"] = winobj.chatgpt_max_token.text().strip()
        params["chatgpt_key"] = winobj.chatgpt_key.text()
        params["chatgpt_api"] = tools.process_openai_api(winobj.chatgpt_api.text().strip())
        params["chatgpt_model"] = winobj.chatgpt_model.currentText()
        params["chatgpt_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        winobj.close()

    winobj.set_chatgpt.clicked.connect(save_chatgpt)
    winobj.test_chatgpt.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'chatgpt_model', 'chatgpt_model'))
    winobj.show()
