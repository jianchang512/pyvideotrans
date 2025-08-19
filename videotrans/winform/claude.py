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
        key = winobj.key.text()
        url = winobj.api.text().strip()
        url = url if url else 'https://api.anthropic.com'
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.model.currentText()
        template = winobj.template.toPlainText()

        config.params["claude_key"] = key
        config.params["claude_api"] = url
        config.params["claude_model"] = model
        config.params["claude_template"] = template
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.CLAUDE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.key.text()
        url = winobj.api.text().strip()
        url = url if url else 'https://api.anthropic.com'
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.model.currentText()
        template = winobj.template.toPlainText()
        with Path(tools.get_prompt_file('claude')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["claude_key"] = key
        config.params["claude_api"] = url
        config.params["claude_model"] = model
        config.params["claude_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.model.currentText()
        winobj.model.clear()
        winobj.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.model.setCurrentText(current_text)
        config.settings['claude_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['claude_model']
        allmodels = config.settings['claude_model'].split(',')
        winobj.model.clear()
        winobj.model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["claude_key"]:
            winobj.key.setText(config.params["claude_key"])
        if config.params["claude_api"]:
            winobj.api.setText(config.params["claude_api"])
        if config.params["claude_model"] and config.params['claude_model'] in allmodels:
            winobj.model.setCurrentText(config.params["claude_model"])
        if config.params["claude_template"]:
            winobj.template.setPlainText(config.params["claude_template"])

    from videotrans.component import ClaudeForm
    winobj = config.child_forms.get('claudew')
    config.params["claude_template"] = tools.get_prompt('claude')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ClaudeForm()
    config.child_forms['claudew'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
