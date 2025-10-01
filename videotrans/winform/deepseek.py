def openwin():
    import json
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
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.deepseek_key.text()
        if not key:
            return tools.show_error(
                '必须填写  密钥 信息' if config.defaulelang == 'zh' else 'Please input Secret')
        model = winobj.deepseek_model.currentText()
        template = winobj.template.toPlainText()

        max_token= winobj.max_token.text().strip()
        config.params["deepseek_max_token"] = max_token

        config.params["deepseek_key"] = key

        config.params["deepseek_model"] = model
        config.params["deepseek_template"] = template
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPSEEK_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        deepseek_key = winobj.deepseek_key.text()
        template = winobj.template.toPlainText()
        model = winobj.deepseek_model.currentText()
        max_token= winobj.max_token.text().strip()
        config.params["deepseek_max_token"] = max_token
        with Path(tools.get_prompt_file('deepseek')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["deepseek_key"] = deepseek_key
        config.params["deepseek_model"] = model
        config.params["deepseek_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.deepseek_model.currentText()
        winobj.deepseek_model.clear()
        winobj.deepseek_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.deepseek_model.setCurrentText(current_text)
        config.settings['deepseek_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))



    from videotrans.component import DeepseekForm
    config.params["deepseek_template"] = tools.get_prompt('deepseek')
    winobj = DeepseekForm()
    config.child_forms['deepseek'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
