

def openwin(init=False):
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
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
        params["index_tts_version"] = index_tts_version
        params["f5tts_role"] = role
        params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        params["diatts_url"] = winobj.diatts_url.text()
        params["indextts_url"] = winobj.indextts_url.text()
        params["sparktts_url"] = winobj.sparktts_url.text()
        params["f5tts_url"] = winobj.f5tts_url.text()
        params["indextts_prompt"] = winobj.indextts_prompt.text()



        params.save()

        test_btn[tts_type].setText(tr('Testing...'))
        import time
        wk = ListenVoice(parent=winobj,
                         queue_tts=[{"text": '你好啊我的朋友,希望你今天开心！', "role": role_test, "filename": TEMP_DIR + f"/{time.time()}-{tts_type}.wav", "tts_type": tts_type}],
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
            elif not Path(ROOT_DIR + f'/f5-tts/{s[0]}').is_file():
                tools.show_error(tr("Please save the audio file in the {}/f5-tts directory",ROOT_DIR))
                return
            role = s[0]
        params['f5tts_role'] = tmp
        return role

    def save():

        index_tts_version = winobj.index_tts_version.currentIndex()
        role = winobj.f5tts_role.toPlainText().strip()

        params["f5tts_role"] = role
        params["index_tts_version"] = index_tts_version
        
        params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        params["diatts_url"] = winobj.diatts_url.text()
        params["indextts_url"] = winobj.indextts_url.text()
        params["sparktts_url"] = winobj.sparktts_url.text()
        params["f5tts_url"] = winobj.f5tts_url.text()
        params["indextts_prompt"] = winobj.indextts_prompt.text()


        params.save()
        tools.set_process(text='f5tts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import F5TTSForm
    Path(ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    winobj = F5TTSForm()
    app_cfg.child_forms['f5tts'] = winobj
    winobj.f5tts_role.setPlainText(params.get("f5tts_role",''))
    winobj.index_tts_version.setCurrentIndex(int(params.get('index_tts_version',0)))
    
    winobj.f5tts_url.setText(params.get('f5tts_url',''))
    winobj.sparktts_url.setText(params.get('sparktts_url',''))
    winobj.indextts_url.setText(params.get('indextts_url',''))
    winobj.diatts_url.setText(params.get('diatts_url',''))
    winobj.voxcpmtts_url.setText(params.get('voxcpmtts_url',''))
    winobj.indextts_prompt.setText(params.get('indextts_prompt',''))

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
