

def openwin():
    from pathlib import Path
    from videotrans.winform import get_cls
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform._helpers import make_feed_translator


    winobj = get_cls(Path(__file__).stem)()

    feed = make_feed_translator(winobj, "test")

    def test():
        key = winobj.deepl_key.text().strip()
        if not key:
            return show_error(tr("Please input auth Secret"))
        params['deepl_key'] = key
        params['deepl_api'] = winobj.deepl_api.text().strip()
        params['deepl_gid'] = winobj.deepl_gid.text().strip()
        params.save()
        winobj.test.setText(tr("Testing..."))
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.DEEPL_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params['deepl_key'] = winobj.deepl_key.text().strip()
        params['deepl_api'] = winobj.deepl_api.text().strip()
        params['deepl_gid'] = winobj.deepl_gid.text().strip()
        params.save()
        winobj.close()

    if params['deepl_key']:
        winobj.deepl_key.setText(str(params['deepl_key']))
    if params['deepl_api']:
        winobj.deepl_api.setText(str(params['deepl_api']))
    if params['deepl_gid']:
        winobj.deepl_gid.setText(str(params['deepl_gid']))
    winobj.set_deepl.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
