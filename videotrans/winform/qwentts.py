def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,logs
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_qwentts.setText(tr("Test"))

    def test():
        key = winobj.qwentts_key.text().strip()
        if not key:
            tools.show_error("API Key is empty")
            return

        model = winobj.qwentts_model.currentText()
        config.params["qwentts_key"] = key
        config.params["qwentts_model"] = model
        config.getset_params(config.params)
        config.settings['qwentts_models']=winobj.qwentts_modellist.toPlainText().strip()
        config.parse_init(config.settings)
        winobj.test_qwentts.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": config.settings.get('qwentts_role','').split(',')[0],
            "filename": config.TEMP_DIR + f"/{time.time()}-qwen.wav",
            "tts_type": tts.QWEN_TTS}],
                         language="zh",
                         tts_type=tts.QWEN_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save_qwentts():
        key = winobj.qwentts_key.text()

        model = winobj.qwentts_model.currentText()

        config.params["qwentts_key"] = key
        config.params["qwentts_model"] = model

        config.getset_params(config.params)

        config.settings['qwentts_models']=winobj.qwentts_modellist.toPlainText().strip()
        config.parse_init(config.settings)
        tools.set_process(text='qwentts', type="refreshtts")
        winobj.close()


        



    from videotrans.component.set_form import QwenTTSForm
    winobj = QwenTTSForm()
    config.child_forms['qwentts'] = winobj
    winobj.update_ui()

    winobj.set_qwentts.clicked.connect(save_qwentts)
    winobj.test_qwentts.clicked.connect(test)
    winobj.show()
