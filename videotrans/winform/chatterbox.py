def openwin():
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            tools.set_process(text='chatterbox', type="refreshtts")
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
        config.params["chatterbox_url"] = url
        config.params["chatterbox_role"] = winobj.role.toPlainText().strip()
        config.params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        config.params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)

        winobj.test.setText('Testing...')
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{"text": 'Hello,my friend,welcom to China', "role": getrole(),
                                                    "filename": config.TEMP_HOME + f"/test-chatterbox.wav",
                                                    "tts_type": tts.CHATTERBOX_TTS}], language="en",
                         tts_type=tts.CHATTERBOX_TTS)
        wk.uito.connect(feed)
        wk.start()
        config.getset_params(config.params)

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip()
            if not Path(config.ROOT_DIR + f"/chatterbox/{s}").exists():
                tools.show_error(
                    f"请确保 chatterbox 文件夹内存在音频文件 {s}" if config.defaulelang == 'zh' else f'Please make sure that the audio file {s} exists in the chatterbox folder',
                    False)
                return

            role = s

        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()

        config.params["chatterbox_url"] = url
        config.params["chatterbox_role"] = role

        config.params["chatterbox_cfg_weight"] = min(max(float(winobj.cfg_weight.text()), 0.0), 1.0)
        config.params["chatterbox_exaggeration"] = min(max(float(winobj.exaggeration.text()), 0.25), 2.0)

        config.getset_params(config.params)
        tools.set_process(text='chatterbox', type="refreshtts")

        winobj.close()

    from videotrans.component import ChatterboxForm
    winobj = config.child_forms.get('chatterboxw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatterboxForm()
    config.child_forms['chatterboxw'] = winobj
    if config.params["chatterbox_url"]:
        winobj.api_url.setText(config.params["chatterbox_url"])
    if config.params["chatterbox_role"]:
        winobj.role.setPlainText(config.params["chatterbox_role"])
    if config.params["chatterbox_cfg_weight"]:
        winobj.cfg_weight.setText(str(config.params["chatterbox_cfg_weight"]))
    if config.params["chatterbox_exaggeration"]:
        winobj.exaggeration.setText(str(config.params["chatterbox_exaggeration"]))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
