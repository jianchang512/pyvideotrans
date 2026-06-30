def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import OpenrouterForm

    winobj = OpenrouterForm()
    app_cfg.child_forms['openrouter'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.openrouter_key.text()
        if not key:
            return tools.show_error(tr("Please input Secret"))
        params["openrouter_key"] = key
        params["openrouter_model"] = winobj.openrouter_model.currentText()
        params["openrouter_max_token"] = winobj.max_token.text().strip()
        params["openrouter_reasoning_effort"] = winobj.reasoning_effort.currentText()
        winobj.test.setText(tr("Testing..."))
        params.save()
        task = TestSrtTrans(parent=winobj, translator_type=translator.OPENROUTER_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["openrouter_key"] = winobj.openrouter_key.text()
        params["openrouter_model"] = winobj.openrouter_model.currentText()
        params["openrouter_max_token"] = winobj.max_token.text().strip()
        params["openro_reasoning_effort"] = winobj.reasoning_effort.currentText()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'openrouter_model', 'openrouter_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
