def openwin():
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)

        winobj.test.setText('Test')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()
        if not role:
            tools.show_error('必须填写参考音频才可测试', False)
            return
        role_test = getrole()
        if not role_test:
            return
        is_whisper = winobj.is_whisper.isChecked()
        config.params["f5tts_is_whisper"] = is_whisper
        config.params["f5tts_url"] = url
        config.params["f5tts_role"] = role
        config.params["f5tts_ttstype"] = winobj.ttstype.currentText()
        config.getset_params(config.params)

        winobj.test.setText('测试中请稍等...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": '你好啊我的朋友', "role": role_test,
                                                    "filename": config.TEMP_HOME + f"/test-f5tts.wav",
                                                    "tts_type": tts.F5_TTS}], language="zh", tts_type=tts.F5_TTS)
        wk.uito.connect(feed)
        wk.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                tools.show_error("每行都必须以#分割为2部分，格式为   音频名称.wav#音频文字内容", False)
                return
            if not s[0].endswith(".wav"):
                tools.show_error("每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容", False)
                return
            elif not Path(config.ROOT_DIR + f'/f5-tts/{s[0]}').is_file():
                tools.show_error(f"请将音频文件存放在 {config.ROOT_DIR}/f5-tts 目录下", False)
                return
            role = s[0]
        config.params['f5tts_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()
        is_whisper = winobj.is_whisper.isChecked()

        config.params["f5tts_url"] = url
        config.params["f5tts_role"] = role
        config.params["f5tts_is_whisper"] = is_whisper
        config.params["f5tts_ttstype"] = winobj.ttstype.currentText()
        print(winobj.ttstype.currentText())
        config.getset_params(config.params)
        tools.set_process(text='f5tts', type="refreshtts")
        winobj.close()

    from videotrans.component import F5TTSForm
    winobj = config.child_forms.get('f5ttsw')
    Path(config.ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = F5TTSForm()
    config.child_forms['f5ttsw'] = winobj
    if config.params["f5tts_url"]:
        winobj.api_url.setText(config.params["f5tts_url"])
    if config.params["f5tts_role"]:
        winobj.role.setPlainText(config.params["f5tts_role"])
    if config.params["f5tts_is_whisper"]:
        winobj.is_whisper.setChecked(bool(config.params.get("f5tts_is_whisper")))
    if config.params["f5tts_ttstype"]:
        winobj.ttstype.setCurrentText(config.params["f5tts_ttstype"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
