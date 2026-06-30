def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import XiaomiForm

    winobj = XiaomiForm()
    app_cfg.child_forms['xiaomi'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        params["xiaomi_key"] = winobj.xiaomi_key.text()
        params["xiaomi_model"] = winobj.model.currentText()
        params["xiaomi_maxtoken"] = winobj.xiaomi_maxtoken.text()
        params["xiaomi_thinking"] = winobj.xiaomi_thinking.isChecked()
        params["xiaomi_ttsmodel"] = winobj.ttsmodel.currentText()
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.XIAOMI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["xiaomi_key"] = winobj.xiaomi_key.text()
        params["xiaomi_model"] = winobj.model.currentText()
        params["xiaomi_maxtoken"] = winobj.xiaomi_maxtoken.text()
        params["xiaomi_thinking"] = winobj.xiaomi_thinking.isChecked()
        params["xiaomi_ttsmodel"] = winobj.ttsmodel.currentText()
        params.save()
        winobj.close()

    winobj.set_xiaomi.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'model', 'xiaomi_model'))
    winobj.show()
