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
        url = winobj.clone_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['clone_api'] = url
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": config.params["clone_voicelist"][1] if len(config.params["clone_voicelist"]) > 1 else '',
            "filename": config.TEMP_HOME + f"/test-clonevoice.wav",
            "tts_type": tts.CLONE_VOICE_TTS}],
                         language="zh",
                         tts_type=tts.CLONE_VOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.clone_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        url = url.rstrip('/')
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["clone_api"] = url
        config.getset_params(config.params)
        tools.set_process(text='clone', type="refreshtts")
        winobj.close()

    from videotrans.component import CloneForm
    winobj = config.child_forms.get('clonew')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = CloneForm()
    config.child_forms['clonew'] = winobj
    if config.params["clone_api"]:
        winobj.clone_address.setText(config.params["clone_api"])
    winobj.set_clone.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
