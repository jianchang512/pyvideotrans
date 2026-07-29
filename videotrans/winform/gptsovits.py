

def openwin():
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure.config import tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component.set_form import GPTSoVITSForm

    winobj = GPTSoVITSForm()
    app_cfg.child_forms['gptsovits'] = winobj

    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr('Test'))

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        msg=tr("Each line must be separated into three parts by the English # sign, in the format of audio name.wav#audio text content#audio language code")
        if not tmp:
            show_error(msg)
            return
        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 3:
                show_error(msg)
                return
            role = s[0]
        if not role:
            show_error(msg)
            return
        return role

    def _fix_url(url):
        if not url.startswith('http'):
            return 'http://' + url
        return url

    def test():
        params["gptsovits_url"] = _fix_url(winobj.api_url.text().strip())
        params["gptsovits_isv2"] = winobj.is_v2.isChecked()
        params["gptsovits_role"] = winobj.role.toPlainText().strip()
        params.save()
        role = getrole()
        if not role:
            return
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '\u4f60\u597d\u554a\u6211\u7684\u670b\u53cb',
            "role": role,
            "filename": config.TEMP_DIR + f"/{time.time()}-gptsovits.wav",
            "tts_type": tts.GPTSOVITS_TTS}],
                         language="zh",
                         tts_type=tts.GPTSOVITS_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["gptsovits_url"] = _fix_url(winobj.api_url.text().strip())
        params["gptsovits_role"] = winobj.role.toPlainText().strip()
        params["gptsovits_isv2"] = winobj.is_v2.isChecked()
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()

    winobj.api_url.setText(str(params.get("gptsovits_url",'')))
    winobj.role.setPlainText(str(params.get("gptsovits_role",'')))
    winobj.is_v2.setChecked(str(params.get("gptsovits_isv2",'')))
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
