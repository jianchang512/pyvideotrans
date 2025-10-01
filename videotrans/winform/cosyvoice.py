def openwin():
    from PySide6 import QtWidgets
    from pathlib import Path
    from pydub import AudioSegment

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
        
        role = winobj.role.toPlainText().strip()
        if not role:
            return tools.show_error('必须填写参考音频')
        
        config.params["cosyvoice_url"] = url

        config.params["cosyvoice_role"] = role
        
        config.getset_params(config.params)
        
        for it in role.split("\n"):
            file=it.split('#')[0]
            file=config.ROOT_DIR+f'/f5-tts/{file}'
            if not Path(file).exists():
                return tools.show_error(f'参考音频不存在: {file}')
            if not file.endswith('.wav'):
                return tools.show_error(f'请上传wav格式的参考音频: {file}')
            if len(AudioSegment.from_file(file))>9990:
                return tools.show_error(f'请确保参考音频时长小于10s: {file}')
        
        
        winobj.test.setText('测试中请稍等...')
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": role.split("\n")[0].split('#')[0],
            "filename": config.TEMP_HOME + f"/{time.time()}-cosyvoice.wav",
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
        if not role:
            return tools.show_error('必须填写参考音频')

        config.params["cosyvoice_url"] = url

        config.params["cosyvoice_role"] = role
        config.getset_params(config.params)
        tools.set_process(text='cosyvoice', type="refreshtts")

        winobj.close()

    from videotrans.component import CosyVoiceForm
    winobj = CosyVoiceForm()
    config.child_forms['cosyvoice'] = winobj
    if config.params["cosyvoice_url"]:
        winobj.api_url.setText(config.params["cosyvoice_url"])
    if config.params["cosyvoice_role"]:
        winobj.role.setPlainText(config.params["cosyvoice_role"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
