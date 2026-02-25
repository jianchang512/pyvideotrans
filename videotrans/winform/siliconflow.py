def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
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
        key = winobj.guiji_key.text()
        if not key:
            return tools.show_error(
                tr("Please input Secret"))
        model = winobj.guiji_model.currentText()
        max_token= winobj.max_token.text().strip()
        params["guiji_max_token"] = max_token

        params["guiji_key"] = key

        params["guiji_model"] = model
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.SILICONFLOW_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        guiji_key = winobj.guiji_key.text()
        model = winobj.guiji_model.currentText()
        max_token= winobj.max_token.text().strip()
        params["guiji_max_token"] = max_token
        params["guiji_key"] = guiji_key
        params["guiji_model"] = model
        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.guiji_model.currentText()
        winobj.guiji_model.clear()
        winobj.guiji_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.guiji_model.setCurrentText(current_text)
        settings['guiji_model'] = t
        settings.save()



    from videotrans.component.set_form import SiliconflowForm
    winobj = SiliconflowForm()
    app_cfg.child_forms['siliconflow'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
