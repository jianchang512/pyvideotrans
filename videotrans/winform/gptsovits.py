def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,app_cfg, params
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans import tts
    import time
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


        role = getrole()
        if not role:return

        winobj.test.setText(tr('Testing...'))
        params["gptsovits_url"] = url
        params["gptsovits_isv2"] = winobj.is_v2.isChecked()
        params["gptsovits_role"] = winobj.role.toPlainText().strip()
        params.save()

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
        msg=tr("Each line must be separated into three parts by the English # sign, in the format of audio name.wav#audio text content#audio language code")
        if not tmp:
            tools.show_error(msg)
            return
        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 3:
                tools.show_error(msg)
                return
            role = s[0]
        if not role:
            tools.show_error(msg)
            return
        return role

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()

        params["gptsovits_url"] = url
        params["gptsovits_role"] = role
        params["gptsovits_isv2"] = winobj.is_v2.isChecked()
        params.save()

        tools.set_process(text='', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import GPTSoVITSForm

    winobj = GPTSoVITSForm()
    app_cfg.child_forms['gptsovits'] = winobj
    winobj.api_url.setText(params.get("gptsovits_url",''))
    winobj.role.setPlainText(params.get("gptsovits_role",''))
    winobj.is_v2.setChecked(params.get("gptsovits_isv2",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
