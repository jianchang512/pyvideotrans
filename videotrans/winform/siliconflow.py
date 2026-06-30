def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import SiliconflowForm

    winobj = SiliconflowForm()
    app_cfg.child_forms['siliconflow'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.guiji_key.text()
        if not key:
            return tools.show_error(tr("Please input Secret"))
        params["guiji_key"] = key
        params["guiji_model"] = winobj.guiji_model.currentText()
        params["guiji_max_token"] = winobj.max_token.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.SILICONFLOW_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["guiji_key"] = winobj.guiji_key.text()
        params["guiji_model"] = winobj.guiji_model.currentText()
        params["guiji_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'guiji_model', 'guiji_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
