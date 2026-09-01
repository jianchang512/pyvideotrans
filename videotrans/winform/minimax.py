

def openwin():
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import MiniMaxForm

    winobj = MiniMaxForm()
    app_cfg.child_forms['minimax'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.minimax_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["minimax_key"] = key
        params["minimax_model"] = winobj.minimax_model.currentText()
        params["minimax_max_token"] = winobj.max_token.text()
        params["minimax_thinking"] = winobj.minimax_thinking.isChecked()
        api = winobj.minimax_api.text().strip()
        if api:
            params["minimax_api"] = api
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.MINIMAX_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["minimax_key"] = winobj.minimax_key.text().strip()
        params["minimax_model"] = winobj.minimax_model.currentText()
        params["minimax_max_token"] = winobj.max_token.text()
        params["minimax_thinking"] = winobj.minimax_thinking.isChecked()
        api = winobj.minimax_api.text().strip()
        if api:
            params["minimax_api"] = api
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'minimax_model', 'minimax_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
