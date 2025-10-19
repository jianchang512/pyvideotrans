def openwin():
    import json
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr
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
            return tools.show_error('必须填写API key和推理接入点')

        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        winobj.test_zijiehuoshan.setText(tr("Testing..."))

        task = TestSrtTrans(parent=winobj, translator_type=translator.ZIJIE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_zijiehuoshan():
        key = winobj.zijiehuoshan_key.text()

        model = winobj.zijiehuoshan_model.currentText()

        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model

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



    from videotrans.component.set_form import ZijiehuoshanForm
    winobj = ZijiehuoshanForm()
    config.child_forms['zijie'] = winobj
    winobj.update_ui()
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_zijiehuoshan.clicked.connect(save_zijiehuoshan)
    winobj.test_zijiehuoshan.clicked.connect(test)
    winobj.show()
