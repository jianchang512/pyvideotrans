def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.minimax_key.text()
        if not key:
            return tools.show_error(
                tr("Please input Secret"))
        model = winobj.minimax_model.currentText()
        max_token = winobj.max_token.text()


        params["minimax_key"] = key
        params["minimax_max_tokens"] = max_token
        api = winobj.minimax_api.text().strip()
        if api:
            params["minimax_api"] = api

        params["minimax_model"] = model
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.MINIMAX_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        minimax_key = winobj.minimax_key.text()
        model = winobj.minimax_model.currentText()
        api = winobj.minimax_api.text().strip()
        max_token = winobj.max_token.text()

        params["minimax_key"] = minimax_key
        params["minimax_model"] = model
        params["minimax_max_tokens"] = max_token
        if api:
            params["minimax_api"] = api
        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.minimax_model.currentText()
        winobj.minimax_model.clear()
        winobj.minimax_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.minimax_model.setCurrentText(current_text)
        settings['minimax_model'] = t
        settings.save()



    from videotrans.component.set_form import MiniMaxForm
    winobj = MiniMaxForm()
    app_cfg.child_forms['minimax'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
