def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.kokoro_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['kokoro_api'] = url
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": 'hello,my friend',
            "role": "af_alloy",
            "filename": config.TEMP_HOME + f"/test-kokoro.wav",
            "tts_type": tts.KOKORO_TTS}],
                         language="en",
                         tts_type=tts.KOKORO_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.kokoro_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["kokoro_api"] = url
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import KokoroForm
    winobj = config.child_forms.get('kokorow')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = KokoroForm()
    config.child_forms['kokorow'] = winobj
    if config.params["kokoro_api"]:
        winobj.kokoro_address.setText(config.params["kokoro_api"])
    winobj.set_kokoro.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
