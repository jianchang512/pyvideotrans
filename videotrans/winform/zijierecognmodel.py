def openwin():
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans import recognition
    from videotrans.util import tools
    from videotrans.util.TestSTT import TestSTT
    from videotrans.winform._helpers import make_feed_stt
    from videotrans.component.set_form import ZijierecognmodelForm

    winobj = ZijierecognmodelForm()
    app_cfg.child_forms['zijierecognmodel'] = winobj
    winobj.update_ui()

    feed = make_feed_stt(winobj, "test")

    def test():
        appid = winobj.zijierecognmodel_appid.text().strip()
        access = winobj.zijierecognmodel_token.text().strip()
        if not appid or not access:
            return tools.show_error(tr('Appid access and cluster are required'))
        params["zijierecognmodel_appid"] = appid
        params["zijierecognmodel_token"] = access
        task = TestSTT(parent=winobj, recogn_type=recognition.ZIJIE_RECOGN_MODEL)
        task.uito.connect(feed)
        task.start()
        winobj.test.setText(tr('Testing...'))

    def save():
        params["zijierecognmodel_appid"] = winobj.zijierecognmodel_appid.text().strip()
        params["zijierecognmodel_token"] = winobj.zijierecognmodel_token.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
