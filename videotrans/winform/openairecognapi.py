def openwin():
    import json

    from PySide6 import QtWidgets
    from videotrans.configure.config import tr
    from videotrans.configure import config
    # set chatgpt
    from videotrans.util import tools

    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test_openairecognapi.setText(
            tr("Test"))

    def test():
        key = winobj.openairecognapi_key.text()
        prompt = winobj.openairecognapi_prompt.text()
        url = winobj.openairecognapi_url.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.openairecognapi_model.currentText()

        config.params["openairecognapi_key"] = key
        config.params["openairecognapi_url"] = url
        config.params["openairecognapi_model"] = model
        config.params["openairecognapi_prompt"] = prompt
        winobj.test_openairecognapi.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.OPENAI_API)
        task.uito.connect(feed)
        task.start()

    def save_openairecognapi():
        key = winobj.openairecognapi_key.text()
        prompt = winobj.openairecognapi_prompt.text()
        url = winobj.openairecognapi_url.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if not url.startswith('http'):
            url = 'http://' + url

        model = winobj.openairecognapi_model.currentText()

        config.params["openairecognapi_key"] = key
        config.params["openairecognapi_url"] = url
        config.params["openairecognapi_model"] = model
        config.params["openairecognapi_prompt"] = prompt
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.openairecognapi_model.currentText()
        winobj.openairecognapi_model.clear()
        winobj.openairecognapi_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.openairecognapi_model.setCurrentText(current_text)
        config.settings['openairecognapi_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))



    from videotrans.component.set_form import OpenaiRecognAPIForm
    winobj = OpenaiRecognAPIForm()
    config.child_forms['openairecognapi'] = winobj
    winobj.update_ui()
    winobj.set_openairecognapi.clicked.connect(save_openairecognapi)
    winobj.test_openairecognapi.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
