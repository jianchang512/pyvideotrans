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
        winobj.test_xaitts.setText(tr("Test"))

    def test():
        key = winobj.xaitts_key.text()
        params["xaitts_key"] = key
        params.save()
        winobj.test_xaitts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": 'eve',
            "filename": TEMP_DIR + f"/{time.time()}-xai.wav",
            "tts_type": tts.XAI_TTS}],
                         language="zh",
                         tts_type=tts.XAI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        key = winobj.xaitts_key.text()

        params["xaitts_key"] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import XAITTSForm
    winobj = XAITTSForm()
    app_cfg.child_forms['xaitts'] = winobj
    winobj.update_ui()
    winobj.test_xaitts.clicked.connect(test)
    winobj.set_xaitts.clicked.connect(save)
    winobj.show()
