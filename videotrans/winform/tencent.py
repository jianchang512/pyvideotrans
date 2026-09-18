

def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.util.help_misc import show_error
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_feed_translator


    winobj = get_cls(Path(__file__).stem)()

    feed = make_feed_translator(winobj, "test")

    def test():
        SecretId = winobj.tencent_SecretId.text().strip()
        SecretKey = winobj.tencent_SecretKey.text().strip()
        if not SecretId or not SecretKey:
            return show_error(tr("Please input SecretId and SecretKey"))
        params["tencent_SecretId"] = SecretId
        params["tencent_SecretKey"] = SecretKey
        params["tencent_termlist"] = winobj.tencent_term.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.TENCENT_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        params["tencent_SecretId"] = winobj.tencent_SecretId.text().strip()
        params["tencent_SecretKey"] = winobj.tencent_SecretKey.text().strip()
        params["tencent_termlist"] = winobj.tencent_term.text().strip()
        params.save()
        winobj.close()

    if params["tencent_SecretId"]:
        winobj.tencent_SecretId.setText(str(params["tencent_SecretId"]))
    if params["tencent_SecretKey"]:
        winobj.tencent_SecretKey.setText(str(params["tencent_SecretKey"]))
    if params["tencent_termlist"]:
        winobj.tencent_term.setText(str(params["tencent_termlist"]))
    winobj.set_tencent.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
