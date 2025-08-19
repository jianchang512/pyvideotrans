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
        winobj.test.setText('测试api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["cosyvoice_url"] = url
        winobj.test.setText('测试中请稍等...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": '中文女',
            "filename": config.TEMP_HOME + f"/test-cosyvoice.wav",
            "tts_type": tts.COSYVOICE_TTS}],
                         language="zh",
                         tts_type=tts.COSYVOICE_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()

        config.params["cosyvoice_url"] = url

        config.params["cosyvoice_role"] = role
        config.getset_params(config.params)
        tools.set_process(text='cosyvoice', type="refreshtts")

        winobj.close()

    from videotrans.component import CosyVoiceForm
    winobj = config.child_forms.get('cosyvoicew')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = CosyVoiceForm()
    config.child_forms['cosyvoicew'] = winobj
    if config.params["cosyvoice_url"]:
        winobj.api_url.setText(config.params["cosyvoice_url"])
    if config.params["cosyvoice_role"]:
        winobj.role.setPlainText(config.params["cosyvoice_role"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
