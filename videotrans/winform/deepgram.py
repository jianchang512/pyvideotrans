def openwin():
    from PySide6 import QtWidgets

    from videotrans import recognition
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            tools.show_error('必须填写 API Key' if config.defaulelang == 'zh' else 'Must fill in the API Key', False)
            return
        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
        winobj.test.setText('测试...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSTT(parent=winobj, recogn_type=recognition.Deepgram, model_name="whisper-large")
        task.uito.connect(feed)
        task.start()

    def save():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            tools.show_error('必须填写 API Key' if config.defaulelang == 'zh' else 'Must fill in the API Key', False)
            return

        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepgramForm
    winobj = config.child_forms.get('deepgramw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepgramForm()
    config.child_forms['deepgramw'] = winobj
    if config.params["deepgram_apikey"]:
        winobj.apikey.setText(config.params["deepgram_apikey"])
    if config.params["deepgram_utt"]:
        winobj.utt.setText(str(config.params["deepgram_utt"]))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
