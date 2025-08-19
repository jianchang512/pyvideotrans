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
        from videotrans import tts
        winobj.test.setText('测试中请稍等...')

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
            "filename": config.TEMP_HOME + f"/test-gptsovits.wav",
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
                tools.show_error("每行都必须以英文#号分割为三部分，格式为   音频名称.wav#音频文字内容#音频语言代码", False)
                return
            if not s[0].endswith(".wav"):
                tools.show_error("每行都必须以英文#号分割为三部分，格式为  音频名称.wav#音频文字内容#音频语言代码 ,并且第一部分为.wav结尾的音频名称", False)
                return
            if s[2] not in ['zh', 'ja', 'en']:
                tools.show_error("每行必须以英文#号分割为三部分，格式为 音频名称.wav#音频文字内容#音频语言代码 ,并且第三部分语言代码只能是 zh或en或ja", False)
                return
            role = s[0]
        config.params['gptsovits_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
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

    from videotrans.component import GPTSoVITSForm
    winobj = config.child_forms.get('gptsovitsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = GPTSoVITSForm()
    config.child_forms['gptsovitsw'] = winobj
    if config.params["gptsovits_url"]:
        winobj.api_url.setText(config.params["gptsovits_url"])
    if config.params["gptsovits_extra"]:
        winobj.extra.setText(config.params["gptsovits_extra"])
    if config.params["gptsovits_role"]:
        winobj.role.setPlainText(config.params["gptsovits_role"])
    if config.params["gptsovits_isv2"]:
        winobj.is_v2.setChecked(config.params["gptsovits_isv2"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
