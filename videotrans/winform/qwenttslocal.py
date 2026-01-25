def openwin():
    from PySide6 import QtWidgets
    from pathlib import Path
    from pydub import AudioSegment
    from videotrans.configure.config import tr

    from videotrans.configure import config
    from videotrans.util import tools
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
        
        role = winobj.role.toPlainText().strip()
        instruct_text = winobj.instruct_text.text()
        config.params["qwenttslocal_prompt"] = instruct_text


        config.params["qwenttslocal_url"] = url

        config.params["qwenttslocal_refaudio"] = role

        config.getset_params(config.params)
        # if not role:
        #     return tools.show_error(tr("Please upload reference audio in wav format"))
        if role:
            for it in role.split("\n"):
                file=it.split('#')[0]
                file=config.ROOT_DIR+f'/f5-tts/{file}'
                if not Path(file).exists():
                    return tools.show_error(tr("No reference audio {} exists",file))
                if not file.endswith('.wav'):
                    return tools.show_error(tr('Please upload reference audio in wav format'))

        
        
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友,希望你的每一天都美好愉快',
            "role": role.split("\n")[0].split('#')[0] if role else 'Vivian',
            "filename": config.TEMP_DIR + f"/{time.time()}-qwenttslocal.wav",
            "tts_type": tts.QWEN3LOCAL_TTS}],
                         language="zh-cn",
                         tts_type=tts.QWEN3LOCAL_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()
        instruct_text = winobj.instruct_text.text()
        config.params["qwenttslocal_prompt"] = instruct_text


        config.params["qwenttslocal_url"] = url

        config.params["qwenttslocal_refaudio"] = role

        config.getset_params(config.params)

        tools.set_process(text='qwenttslocal', type="refreshtts")

        winobj.close()

    from videotrans.component.set_form import QwenttsLocalForm
    winobj = QwenttsLocalForm()
    config.child_forms['qwenttslocal'] = winobj
    if config.params["qwenttslocal_url"]:
        winobj.api_url.setText(config.params["qwenttslocal_url"])
    if config.params["qwenttslocal_refaudio"]:
        winobj.role.setPlainText(config.params["qwenttslocal_refaudio"])
    if config.params.get("qwenttslocal_prompt"):
        winobj.instruct_text.setText(config.params.get("qwenttslocal_prompt"))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
