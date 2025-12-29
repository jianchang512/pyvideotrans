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
        key = winobj.deepseek_key.text()
        if not key:
            return tools.show_error(
                tr("Please input Secret"))
        model = winobj.deepseek_model.currentText()


        config.params["deepseek_key"] = key

        config.params["deepseek_model"] = model
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPSEEK_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        deepseek_key = winobj.deepseek_key.text()
        model = winobj.deepseek_model.currentText()

        config.params["deepseek_key"] = deepseek_key
        config.params["deepseek_model"] = model
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



    from videotrans.component.set_form import DeepseekForm
    winobj = DeepseekForm()
    config.child_forms['deepseek'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
