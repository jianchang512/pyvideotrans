

def openwin():
    import webbrowser
    from PySide6 import QtWidgets
    from videotrans import translator

    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools

    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_ai302.setText(tr("Test"))

    def test():
        key = winobj.ai302_key.text()
        model = winobj.ai302_model.currentText()
        model_recogn = winobj.ai302_model_recogn.currentText()

        params["ai302_key"] = key
        params["ai302_model"] = model
        params["ai302_model_recogn"] = model_recogn

        winobj.test_ai302.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.AI302_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_ai302():
        key = winobj.ai302_key.text()
        model = winobj.ai302_model.currentText()
        model_recogn = winobj.ai302_model_recogn.currentText()

        params["ai302_key"] = key
        params["ai302_model"] = model
        params["ai302_model_recogn"] = model_recogn

        params.save()
        winobj.close()



    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.ai302_model.currentText()
        winobj.ai302_model.clear()
        winobj.ai302_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.ai302_model.setCurrentText(current_text)
        settings['ai302_models'] = t
        settings.save()


    from videotrans.component.set_form import AI302Form


    winobj = AI302Form()
    app_cfg.child_forms['ai302'] = winobj
    winobj.update_ui()

    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_ai302.clicked.connect(save_ai302)
    winobj.test_ai302.clicked.connect(test)
    winobj.label_0.clicked.connect(lambda: webbrowser.open_new_tab("https://pyvideotrans.com/302ai"))
    winobj.show()
