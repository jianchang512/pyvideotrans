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
        winobj.test_zijiehuoshan.setText('测试')

    def test():
        key = winobj.zijiehuoshan_key.text()
        model = winobj.zijiehuoshan_model.currentText()
        if not key or not model.strip():
            return tools.show_error('必须填写API key和推理接入点', False)

        template = winobj.zijiehuoshan_template.toPlainText()
        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template
        winobj.test_zijiehuoshan.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

        task = TestSrtTrans(parent=winobj, translator_type=translator.ZIJIE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_zijiehuoshan():
        key = winobj.zijiehuoshan_key.text()

        model = winobj.zijiehuoshan_model.currentText()
        template = winobj.zijiehuoshan_template.toPlainText()

        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template
        with Path(tools.get_prompt_file('zijie')).open('w', encoding='utf-8') as f:
            f.write(template)
            f.flush()
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        t_list = [x for x in t.split(',') if x.strip()]
        current_text = winobj.zijiehuoshan_model.currentText()
        winobj.zijiehuoshan_model.clear()
        winobj.zijiehuoshan_model.addItems(t_list)
        if current_text:
            winobj.zijiehuoshan_model.setCurrentText(current_text)
        config.settings['zijiehuoshan_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['zijiehuoshan_model']
        allmodels = config.settings['zijiehuoshan_model'].split(',')
        winobj.zijiehuoshan_model.clear()
        winobj.zijiehuoshan_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["zijiehuoshan_key"]:
            winobj.zijiehuoshan_key.setText(config.params["zijiehuoshan_key"])
        if config.params["zijiehuoshan_model"] and config.params['zijiehuoshan_model'] in allmodels:
            winobj.zijiehuoshan_model.setCurrentText(config.params["zijiehuoshan_model"])
        if config.params["zijiehuoshan_template"]:
            winobj.zijiehuoshan_template.setPlainText(config.params["zijiehuoshan_template"])

    from videotrans.component import ZijiehuoshanForm
    winobj = config.child_forms.get('zijiew')
    config.params["zijiehuoshan_template"] = tools.get_prompt('zijie')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ZijiehuoshanForm()
    config.child_forms['zijiew'] = winobj
    update_ui()
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_zijiehuoshan.clicked.connect(save_zijiehuoshan)
    winobj.test_zijiehuoshan.clicked.connect(test)
    winobj.show()
