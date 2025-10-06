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
        key = winobj.qwenmt_key.text()
        if not key:
            return tools.show_error(
                tr("Please input Secret"))
        model = winobj.qwenmt_model.currentText()
        asr_model = winobj.qwenmt_asr_model.currentText()


        config.params["qwenmt_key"] = key

        config.params["qwenmt_model"] = model
        config.params["qwenmt_asr_model"] = asr_model
        config.params["qwenmt_domains"]=winobj.qwenmt_domains.text()

        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.QWENMT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        qwenmt_key = winobj.qwenmt_key.text()
        model = winobj.qwenmt_model.currentText()
        asr_model = winobj.qwenmt_asr_model.currentText()
        config.params["qwenmt_domains"]=winobj.qwenmt_domains.text()
        config.params["qwenmt_key"] = qwenmt_key
        config.params["qwenmt_model"] = model
        config.params["qwenmt_asr_model"] = asr_model
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.qwenmt_model.currentText()
        winobj.qwenmt_model.clear()
        winobj.qwenmt_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.qwenmt_model.setCurrentText(current_text)
        config.settings['qwenmt_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))



    from videotrans.component import QwenmtForm
    winobj = QwenmtForm()
    config.child_forms['qwenmt'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
