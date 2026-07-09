def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import QwenmtForm

    winobj = QwenmtForm()
    app_cfg.child_forms['qwenmt'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.qwenmt_key.text()
        if not key:
            return tools.show_error(tr("Please input Secret"))
        params["qwenmt_key"] = key
        params["qwenmt_spaceid"] = winobj.qwenmt_spaceid.text().strip()
        params["qwenmt_model"] = winobj.qwenmt_model.currentText()
        params["qwenmt_asr_model"] = winobj.qwenmt_asr_model.currentText()
        params["qwenmt_domains"] = winobj.qwenmt_domains.text()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.QWENMT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["qwenmt_key"] = winobj.qwenmt_key.text()
        params["qwenmt_spaceid"] = winobj.qwenmt_spaceid.text().strip()
        params["qwenmt_model"] = winobj.qwenmt_model.currentText()
        params["qwenmt_asr_model"] = winobj.qwenmt_asr_model.currentText()
        params["qwenmt_domains"] = winobj.qwenmt_domains.text()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'qwenmt_model', 'qwenmt_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
