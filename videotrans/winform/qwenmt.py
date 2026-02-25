def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.qwenmt_key.text()
        if not key:
            return tools.show_error(
                tr("Please input Secret"))
        model = winobj.qwenmt_model.currentText()
        asr_model = winobj.qwenmt_asr_model.currentText()


        params["qwenmt_key"] = key

        params["qwenmt_model"] = model
        params["qwenmt_asr_model"] = asr_model
        params["qwenmt_domains"]=winobj.qwenmt_domains.text()

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.QWENMT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        qwenmt_key = winobj.qwenmt_key.text()
        model = winobj.qwenmt_model.currentText()
        asr_model = winobj.qwenmt_asr_model.currentText()
        params["qwenmt_domains"]=winobj.qwenmt_domains.text()
        params["qwenmt_key"] = qwenmt_key
        params["qwenmt_model"] = model
        params["qwenmt_asr_model"] = asr_model
        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.qwenmt_model.currentText()
        winobj.qwenmt_model.clear()
        winobj.qwenmt_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.qwenmt_model.setCurrentText(current_text)
        settings['qwenmt_model'] = t
        settings.save()



    from videotrans.component.set_form import QwenmtForm
    winobj = QwenmtForm()
    app_cfg.child_forms['qwenmt'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
