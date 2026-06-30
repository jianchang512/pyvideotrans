def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import DeepseekForm

    winobj = DeepseekForm()
    app_cfg.child_forms['deepseek'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.deepseek_key.text()
        if not key:
            return tools.show_error(tr("Please input Secret"))
        params["deepseek_key"] = key
        params["deepseek_model"] = winobj.deepseek_model.currentText()
        params["deepseek_max_token"] = winobj.deepseek_max_token.text()
        params["deepseek_thinking"] = winobj.deepseek_thinking.isChecked()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPSEEK_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["deepseek_key"] = winobj.deepseek_key.text()
        params["deepseek_model"] = winobj.deepseek_model.currentText()
        params["deepseek_max_token"] = winobj.deepseek_max_token.text()
        params["deepseek_thinking"] = winobj.deepseek_thinking.isChecked()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'deepseek_model', 'deepseek_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
