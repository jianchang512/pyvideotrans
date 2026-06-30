def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import ZhipuAIForm

    winobj = ZhipuAIForm()
    app_cfg.child_forms['zhipuai'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.zhipu_key.text()
        if not key:
            return tools.show_error(tr("Please input Secret"))
        params["zhipu_key"] = key
        params["zhipu_model"] = winobj.zhipu_model.currentText()
        params["zhipu_max_token"] = winobj.max_token.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.ZHIPUAI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["zhipu_key"] = winobj.zhipu_key.text()
        params["zhipu_model"] = winobj.zhipu_model.currentText()
        params["zhipu_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'zhipu_model', 'zhipuai_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
