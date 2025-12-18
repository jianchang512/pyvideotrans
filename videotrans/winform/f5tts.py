

def openwin(init=False):
    from videotrans.configure.config import tr,logs
    from videotrans.configure import config
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans import tts
    

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "Ok", "Test Ok")
        else:
            tools.show_error(d)


        for it in test_btn.values():
            it.setText(tr('Test'))



    def test(tts_type=tts.F5_TTS):
        
        index_tts_version = winobj.index_tts_version.currentIndex()
        role = winobj.f5tts_role.toPlainText().strip()
        if not role:
            tools.show_error(tr('Please input reference audio path'))
            return
        role_test = getrole()
        if not role_test:
            return
        # 通用
        config.params["index_tts_version"] = index_tts_version
        config.params["f5tts_role"] = role
        config.params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        config.params["diatts_url"] = winobj.diatts_url.text()
        config.params["indextts_url"] = winobj.indextts_url.text()
        config.params["sparktts_url"] = winobj.sparktts_url.text()
        config.params["f5tts_url"] = winobj.f5tts_url.text()



        config.getset_params(config.params)

        test_btn[tts_type].setText(tr('Testing...'))
        import time
        print(f'{tts_type}')
        wk = ListenVoice(parent=winobj,
                         queue_tts=[{"text": '你好啊我的朋友,希望你今天开心！', "role": role_test, "filename": config.TEMP_DIR + f"/{time.time()}-{tts_type}.wav", "tts_type": tts_type}],
                         language="zh",
                         tts_type=tts_type)
        wk.uito.connect(feed)
        wk.start()

    def getrole():
        tmp = winobj.f5tts_role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                tools.show_error(tr("Each line must be split into two parts with #, in the format of audio name.wav#audio text content"))
                return
            elif not Path(config.ROOT_DIR + f'/f5-tts/{s[0]}').is_file():
                tools.show_error(tr("Please save the audio file in the {}/f5-tts directory",config.ROOT_DIR))
                return
            role = s[0]
        config.params['f5tts_role'] = tmp
        return role

    def save():

        index_tts_version = winobj.index_tts_version.currentIndex()
        role = winobj.f5tts_role.toPlainText().strip()

        config.params["f5tts_role"] = role
        config.params["index_tts_version"] = index_tts_version
        
        config.params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        config.params["diatts_url"] = winobj.diatts_url.text()
        config.params["indextts_url"] = winobj.indextts_url.text()
        config.params["sparktts_url"] = winobj.sparktts_url.text()
        config.params["f5tts_url"] = winobj.f5tts_url.text()


        config.getset_params(config.params)
        tools.set_process(text='f5tts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import F5TTSForm
    Path(config.ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    winobj = F5TTSForm()
    config.child_forms['f5tts'] = winobj
    winobj.f5tts_role.setPlainText(config.params.get("f5tts_role",''))
    winobj.index_tts_version.setCurrentIndex(int(config.params.get('index_tts_version',0)))
    
    winobj.f5tts_url.setText(config.params.get('f5tts_url',''))
    winobj.sparktts_url.setText(config.params.get('sparktts_url',''))
    winobj.indextts_url.setText(config.params.get('indextts_url',''))
    winobj.diatts_url.setText(config.params.get('diatts_url',''))
    winobj.voxcpmtts_url.setText(config.params.get('voxcpmtts_url',''))

    winobj.save.clicked.connect(save)
    winobj.f5tts_urltest.clicked.connect(lambda: test(tts.F5_TTS))
    winobj.sparktts_urltest.clicked.connect(lambda: test(tts.SPARK_TTS))
    winobj.indextts_urltest.clicked.connect(lambda: test(tts.INDEX_TTS))
    winobj.diatts_urltest.clicked.connect(lambda: test(tts.DIA_TTS))
    winobj.voxcpmtts_urltest.clicked.connect(lambda: test(tts.VOXCPM_TTS))
    winobj.show()
    test_btn={
        tts.F5_TTS:winobj.f5tts_urltest,
        tts.INDEX_TTS:winobj.indextts_urltest,
        tts.SPARK_TTS:winobj.sparktts_urltest,
        tts.DIA_TTS:winobj.diatts_urltest,
        tts.VOXCPM_TTS:winobj.voxcpmtts_urltest,
    }
