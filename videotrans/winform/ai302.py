def openwin():
    import json
    import webbrowser
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans import translator
    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_ai302.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.ai302_key.text()
        model = winobj.ai302_model.currentText()
        template = winobj.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template

        winobj.test_ai302.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSrtTrans(parent=winobj, translator_type=translator.AI302_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_ai302():
        key = winobj.ai302_key.text()
        model = winobj.ai302_model.currentText()
        template = winobj.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template

        with Path(tools.get_prompt_file('ai302')).open('w', encoding='utf-8') as f:
            f.write(template)
            f.flush()
        config.getset_params(config.params)
        winobj.close()

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['ai302_models']
        allmodels = config.settings['ai302_models'].split(',')

        winobj.ai302_model.clear()
        winobj.ai302_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["ai302_key"]:
            winobj.ai302_key.setText(config.params["ai302_key"])
        if config.params["ai302_model"] and config.params["ai302_model"] in allmodels:
            winobj.ai302_model.setCurrentText(config.params["ai302_model"])
        if config.params["ai302_template"]:
            winobj.ai302_template.setPlainText(config.params["ai302_template"])

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.ai302_model.currentText()
        winobj.ai302_model.clear()
        winobj.ai302_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.ai302_model.setCurrentText(current_text)
        config.settings['ai302_models'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    from videotrans.component import AI302Form
    winobj = config.child_forms.get('ai302fyw')
    config.params["ai302_template"] = tools.get_prompt('ai302')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AI302Form()
    config.child_forms['ai302fyw'] = winobj
    update_ui()

    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_ai302.clicked.connect(save_ai302)
    winobj.test_ai302.clicked.connect(test)
    winobj.label_0.clicked.connect(lambda: webbrowser.open_new_tab("https://pyvideotrans.com/302ai"))
    winobj.show()
