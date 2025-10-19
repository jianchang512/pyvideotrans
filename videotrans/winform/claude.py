def openwin():
    import json
    from videotrans.configure.config import tr

    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.key.text()
        url = winobj.api.text().strip()
        url = url if url else 'https://api.anthropic.com'

        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.model.currentText()
        template = winobj.template.toPlainText()

        config.params["claude_key"] = key
        config.params["claude_api"] = url
        config.params["claude_model"] = model
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.CLAUDE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.key.text()
        url = winobj.api.text().strip()
        url = url if url else 'https://api.anthropic.com'
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.model.currentText()

        config.params["claude_key"] = key
        config.params["claude_api"] = url
        config.params["claude_model"] = model
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



    from videotrans.component.set_form import ClaudeForm
    winobj = ClaudeForm()
    config.child_forms['claude'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
