def openwin():
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator
    from videotrans.component.set_form import BaiduForm

    winobj = BaiduForm()
    app_cfg.child_forms['baidu'] = winobj

    feed = make_feed_translator(winobj, "test")

    def test():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        if not appid or not miyue:
            return tools.show_error(tr("Please input appid and Secret"))
        params["baidu_appid"] = appid
        params["baidu_miyue"] = miyue
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.BAIDU_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_baidu():
        params["baidu_appid"] = winobj.baidu_appid.text()
        params["baidu_miyue"] = winobj.baidu_miyue.text()
        params.save()
        winobj.close()

    if params.get("baidu_appid", ''):
        winobj.baidu_appid.setText(str(params.get("baidu_appid", '')))
    if params.get("baidu_miyue", ''):
        winobj.baidu_miyue.setText(str(params.get("baidu_miyue", '')))
    winobj.set_badiu.clicked.connect(save_baidu)
    winobj.test.clicked.connect(test)
    winobj.show()
