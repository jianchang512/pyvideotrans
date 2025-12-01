def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        from videotrans import tts
        import time
        winobj.test.setText(tr('Testing...'))

        extra = winobj.extra.text()
        role = getrole()

        config.params["gptsovits_url"] = url
        config.params["gptsovits_isv2"] = winobj.is_v2.isChecked()

        config.params["gptsovits_url"] = url
        config.params["gptsovits_extra"] = extra

        config.params["gptsovits_isv2"] = winobj.is_v2.isChecked()

        config.getset_params(config.params)

        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": role,
            "filename": config.TEMP_DIR + f"/{time.time()}-gptsovits.wav",
            "tts_type": tts.GPTSOVITS_TTS}],
                         language="zh",
                         tts_type=tts.GPTSOVITS_TTS)
        wk.uito.connect(feed)
        wk.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 3:
                tools.show_error(tr("Each line must be separated into three parts by the English # sign, in the format of audio name.wav#audio text content#audio language code"))
                return
            role = s[0]
        config.params['gptsovits_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url

        extra = winobj.extra.text()
        role = winobj.role.toPlainText().strip()

        config.params["gptsovits_url"] = url
        config.params["gptsovits_extra"] = extra
        config.params["gptsovits_role"] = role
        config.params["gptsovits_isv2"] = winobj.is_v2.isChecked()
        config.getset_params(config.params)

        tools.set_process(text='gptsovits', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import GPTSoVITSForm

    winobj = GPTSoVITSForm()
    config.child_forms['gptsovits'] = winobj
    winobj.api_url.setText(config.params.get("gptsovits_url",''))
    winobj.extra.setText(config.params.get("gptsovits_extra",''))
    winobj.role.setPlainText(config.params.get("gptsovits_role",''))
    winobj.is_v2.setChecked(config.params.get("gptsovits_isv2",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
