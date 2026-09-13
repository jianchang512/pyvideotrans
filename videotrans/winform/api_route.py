def openwin():
    from videotrans.configure.config import tr, params, app_cfg
    from videotrans.util.help_misc import show_error
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels
    from videotrans.component.set_form import ApiRouteForm

    winobj = ApiRouteForm()
    app_cfg.child_forms['api_route'] = winobj
    winobj.update_ui()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.api_route_key.text().strip()
        if not key:
            return show_error(tr("Please input Secret"))
        params["api_route_key"] = key
        params["api_route_model"] = winobj.api_route_model.currentText()
        params["api_route_max_token"] = winobj.max_token.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.API_ROUTE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["api_route_key"] = winobj.api_route_key.text().strip()
        params["api_route_model"] = winobj.api_route_model.currentText()
        params["api_route_max_token"] = winobj.max_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'api_route_model', 'api_route_model'))
    winobj.test.clicked.connect(test)
    winobj.show()
