def openwin():
    import json
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.guiji_key.text()
        model = winobj.guiji_model.currentText()
        template = winobj.template.toPlainText()

        config.params["guiji_key"] = key

        config.params["guiji_model"] = model
        config.params["guiji_template"] = template
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSrtTrans(parent=winobj, translator_type=translator.SILICONFLOW_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        guiji_key = winobj.guiji_key.text()
        template = winobj.template.toPlainText()
        model = winobj.guiji_model.currentText()
        with Path(tools.get_prompt_file('zhipuai')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["guiji_key"] = guiji_key
        config.params["guiji_model"] = model
        config.params["guiji_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.guiji_model.currentText()
        winobj.guiji_model.clear()
        winobj.guiji_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.guiji_model.setCurrentText(current_text)
        config.settings['guiji_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['guiji_model']
        allmodels = config.settings['guiji_model'].split(',')
        winobj.guiji_model.clear()
        winobj.guiji_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["guiji_key"]:
            winobj.guiji_key.setText(config.params["guiji_key"])
        if config.params["guiji_model"]:
            winobj.guiji_model.setCurrentText(config.params["guiji_model"])
        if config.params["guiji_template"]:
            winobj.template.setPlainText(config.params["guiji_template"])

    from videotrans.component import SiliconflowForm
    winobj = config.child_forms.get('siliconfloww')
    config.params["guiji_template"] = tools.get_prompt('zhipuai')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = SiliconflowForm()
    config.child_forms['siliconfloww'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
