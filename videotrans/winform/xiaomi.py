def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,params,settings,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.xiaomi_key.text()
        model = winobj.model.currentText()
        xiaomi_maxtoken = winobj.xiaomi_maxtoken.text()
        params["xiaomi_maxtoken"] = xiaomi_maxtoken
        params["xiaomi_model"] = model
        params["xiaomi_key"] = key
        
        params["xiaomi_thinking"] = winobj.xiaomi_thinking.isChecked()

        ttsmodel = winobj.ttsmodel.currentText()
        params["xiaomi_ttsmodel"] = ttsmodel

        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.XIAOMI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.xiaomi_key.text()
        model = winobj.model.currentText()

        
        xiaomi_maxtoken = winobj.xiaomi_maxtoken.text()
        params["xiaomi_maxtoken"] = xiaomi_maxtoken

        params["xiaomi_model"] = model
        params["xiaomi_key"] = key
        params["xiaomi_thinking"] = winobj.xiaomi_thinking.isChecked()

        ttsmodel = winobj.ttsmodel.currentText()
        params["xiaomi_ttsmodel"] = ttsmodel

        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.model.currentText()
        winobj.model.clear()
        winobj.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.model.setCurrentText(current_text)
        settings['xiaomi_model'] = t
        settings.save()



    from videotrans.component.set_form import XiaomiForm

    winobj = XiaomiForm()
    app_cfg.child_forms['xiaomi'] = winobj
    winobj.update_ui()
    winobj.set_xiaomi.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
