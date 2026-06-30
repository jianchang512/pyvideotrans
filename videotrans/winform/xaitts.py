def openwin():
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import XAITTSForm

    winobj = XAITTSForm()
    app_cfg.child_forms['xaitts'] = winobj
    winobj.update_ui()

    def feed(d):
        if d.startswith("ok"):
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_xaitts.setText(tr("Test"))

    def test():
        params["xaitts_key"] = winobj.xaitts_key.text()
        params.save()
        winobj.test_xaitts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
            "role": 'eve',
            "filename": config.TEMP_DIR + f"/{time.time()}-xai.wav",
            "tts_type": tts.XAI_TTS}],
                         language="zh",
                         tts_type=tts.XAI_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["xaitts_key"] = winobj.xaitts_key.text()
        params.save()
        winobj.close()

    winobj.test_xaitts.clicked.connect(test)
    winobj.set_xaitts.clicked.connect(save)
    winobj.show()
