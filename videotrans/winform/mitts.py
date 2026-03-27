def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_mitts.setText(tr("Test"))

    def test():
        key = winobj.mitts_key.text()
        params["mitts_key"] = key
        params.save()
        winobj.test_mitts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": 'mimo_default',
            "filename": TEMP_DIR + f"/{time.time()}-xiaomi.wav",
            "tts_type": tts.XIAOMI_TTS}],
                         language="zh",
                         tts_type=tts.XIAOMI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        key = winobj.mitts_key.text()

        params["mitts_key"] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import MITTSForm
    winobj = MITTSForm()
    app_cfg.child_forms['mitts'] = winobj
    winobj.update_ui()
    winobj.test_mitts.clicked.connect(test)
    winobj.set_mitts.clicked.connect(save)
    winobj.show()
