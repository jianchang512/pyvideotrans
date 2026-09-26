def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.config import tr, params
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    from pathlib import Path
    from videotrans.winform._helpers import make_feed_stt

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    feed = make_feed_stt(winobj, "test")

    def test():
        params["audexum_key"] = winobj.audexum_key.text().strip()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.AUDEXUM_API)
        task.uito.connect(feed)
        task.start()

    def save():
        params["audexum_key"] = winobj.audexum_key.text().strip()
        params.save()
        winobj.close()

    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
