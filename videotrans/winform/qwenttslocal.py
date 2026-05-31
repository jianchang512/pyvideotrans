def openwin():
    from PySide6 import QtWidgets
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg, params
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
        instruct_text = winobj.instruct_text.text()
        params["qwenttslocal_prompt"] = instruct_text
        params.save()
        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))

        from videotrans import tts
        import time

        winobj.test.setText(tr('Testing...')+f'  {rolename}')
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友,希望你的每一天都美好愉快',
            "role": rolename,
            "filename": config.TEMP_DIR + f"/{time.time()}-qwenttslocal.wav",
            "tts_type": tts.QWEN3LOCAL_TTS}],
                         language="zh-cn",
                         tts_type=tts.QWEN3LOCAL_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        instruct_text = winobj.instruct_text.text()
        params["qwenttslocal_prompt"] = instruct_text
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import QwenttsLocalForm
    winobj = QwenttsLocalForm()
    app_cfg.child_forms['qwenttslocal'] = winobj
    if params.get("qwenttslocal_prompt"):
        winobj.instruct_text.setText(params.get("qwenttslocal_prompt"))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
