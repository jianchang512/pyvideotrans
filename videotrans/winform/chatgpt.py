def openwin():
    import json
    import os
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_chatgpt.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.chatgpt_key.text()
        max_token = winobj.chatgpt_max_token.text().strip()
        url = winobj.chatgpt_api.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.chatgpt_model.currentText()
        template = winobj.chatgpt_template.toPlainText()

        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = url
        config.params["chatgpt_max_token"] = max_token
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template
        winobj.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.CHATGPT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_chatgpt():
        key = winobj.chatgpt_key.text()
        url = winobj.chatgpt_api.text().strip()
        max_token = winobj.chatgpt_max_token.text().strip()
        url = url if url else 'https://api.openai.com/v1'
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.chatgpt_model.currentText()
        template = winobj.chatgpt_template.toPlainText()
        with Path(tools.get_prompt_file('chatgpt')).open('w', encoding='utf-8') as f:
            f.write(template)
            f.flush()
        config.params["chatgpt_max_token"] = max_token
        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = url
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.chatgpt_model.currentText()
        winobj.chatgpt_model.clear()
        winobj.chatgpt_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.chatgpt_model.setCurrentText(current_text)
        config.settings['chatgpt_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['chatgpt_model']
        allmodels = config.settings['chatgpt_model'].split(',')
        winobj.chatgpt_model.clear()
        winobj.chatgpt_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["chatgpt_key"]:
            winobj.chatgpt_key.setText(config.params["chatgpt_key"])
        if config.params["chatgpt_api"]:
            winobj.chatgpt_api.setText(config.params["chatgpt_api"])
        if config.params["chatgpt_model"] and config.params['chatgpt_model'] in allmodels:
            winobj.chatgpt_model.setCurrentText(config.params["chatgpt_model"])
        if config.params["chatgpt_template"]:
            winobj.chatgpt_template.setPlainText(config.params["chatgpt_template"])
        if config.params["chatgpt_max_token"]:
            winobj.chatgpt_max_token.setText(str(config.params["chatgpt_max_token"]))

    from videotrans.component import ChatgptForm
    winobj = config.child_forms.get('chatgptw')
    config.params["chatgpt_template"] = tools.get_prompt('chatgpt')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatgptForm()
    config.child_forms['chatgptw'] = winobj
    update_ui()
    winobj.set_chatgpt.clicked.connect(save_chatgpt)
    winobj.test_chatgpt.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
