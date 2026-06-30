def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt, make_setallmodels
    from videotrans.component.set_form import OpenaiRecognAPIForm

    winobj = OpenaiRecognAPIForm()
    app_cfg.child_forms['openairecognapi'] = winobj
    winobj.update_ui()

    feed = make_feed_stt(winobj, "test_openairecognapi")

    def test():
        params["openairecognapi_key"] = winobj.openairecognapi_key.text()
        params["openairecognapi_url"] = tools.process_openai_api(winobj.openairecognapi_url.text().strip())
        params["openairecognapi_model"] = winobj.openairecognapi_model.currentText()
        params["openairecognapi_prompt"] = winobj.openairecognapi_prompt.text()
        winobj.test_openairecognapi.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.OPENAI_API)
        task.uito.connect(feed)
        task.start()

    def save_openairecognapi():
        params["openairecognapi_key"] = winobj.openairecognapi_key.text()
        params["openairecognapi_url"] = tools.process_openai_api(winobj.openairecognapi_url.text().strip())
        params["openairecognapi_model"] = winobj.openairecognapi_model.currentText()
        params["openairecognapi_prompt"] = winobj.openairecognapi_prompt.text()
        params.save()
        winobj.close()

    winobj.set_openairecognapi.clicked.connect(save_openairecognapi)
    winobj.test_openairecognapi.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'openairecognapi_model', 'openairecognapi_model'))
    winobj.show()
