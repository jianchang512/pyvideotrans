def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        else:
            tools.show_error(d)
        winobj.test_qwentts.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.qwentts_key.text().strip()
        if not key:
            tools.show_error("API Key is empty", False)
            return

        model = winobj.qwentts_model.currentText()
        config.params["qwentts_key"] = key
        config.params["qwentts_model"] = model
        config.getset_params(config.params)
        winobj.test_qwentts.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": winobj.edit_roles.toPlainText().strip().split(',')[0],
            "filename": config.TEMP_HOME + f"/test-qwen.wav",
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
        tools.set_process(text='qwentts', type="refreshtts")
        winobj.close()

    def setedit_roles():
        t = winobj.edit_roles.toPlainText().strip().replace('，', ',').rstrip(',')
        config.params['qwentts_role'] = t
        config.getset_params(config.params)

    def update_ui():
        winobj.qwentts_model.clear()
        winobj.qwentts_model.addItems(['qwen-tts-latest'])
        winobj.edit_roles.setPlainText(config.params['qwentts_role'])

        if config.params["qwentts_key"]:
            winobj.qwentts_key.setText(config.params["qwentts_key"])
        if config.params["qwentts_model"]:
            winobj.qwentts_model.setCurrentText(config.params["qwentts_model"])

    from videotrans.component import QwenTTSForm
    winobj = config.child_forms.get('qwenttsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = QwenTTSForm()
    config.child_forms['qwenttsw'] = winobj
    update_ui()

    winobj.set_qwentts.clicked.connect(save_qwentts)
    winobj.test_qwentts.clicked.connect(test)
    winobj.edit_roles.textChanged.connect(setedit_roles)
    winobj.show()
