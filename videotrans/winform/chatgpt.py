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



    from videotrans.component import ChatgptForm
    config.params["chatgpt_template"] = tools.get_prompt('chatgpt')

    winobj = ChatgptForm()
    config.child_forms['chatgpt'] = winobj
    winobj.update_ui()
    winobj.set_chatgpt.clicked.connect(save_chatgpt)
    winobj.test_chatgpt.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
