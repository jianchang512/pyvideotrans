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
        winobj.test_localllm.setText(tr("Test"))

    def test():
        key = winobj.localllm_key.text()
        url = winobj.localllm_api.text().strip()
        max_token = winobj.localllm_max_token.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.localllm_model.currentText()


        params["localllm_max_token"] = max_token
        params["localllm_key"] = key
        params["localllm_api"] = url
        params["localllm_model"] = model
        winobj.test_localllm.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.LOCALLLM_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_localllm():
        key = winobj.localllm_key.text()
        url = winobj.localllm_api.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.localllm_model.currentText()
        max_token = winobj.localllm_max_token.text().strip()


        params["localllm_key"] = key
        params["localllm_api"] = url
        params["localllm_max_token"] = max_token

        params["localllm_model"] = model

        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.localllm_model.currentText()
        winobj.localllm_model.clear()
        winobj.localllm_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.localllm_model.setCurrentText(current_text)
        settings['localllm_model'] = t
        settings.save()


    from videotrans.component.set_form import LocalLLMForm
    winobj = LocalLLMForm()
    app_cfg.child_forms['localllm'] = winobj
    winobj.update_ui()
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_localllm.clicked.connect(save_localllm)
    winobj.test_localllm.clicked.connect(test)
    winobj.show()
