

def openwin():
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg, params
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
        # 通用
        params["index_tts_version"] = index_tts_version
        params["voxcpmtts_version"] = winobj.voxcpmtts_version.currentText()
        params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        params["diatts_url"] = winobj.diatts_url.text()
        params["indextts_url"] = winobj.indextts_url.text()
        params["sparktts_url"] = winobj.sparktts_url.text()
        params["f5tts_url"] = winobj.f5tts_url.text()
        params["confuciustts_url"] = winobj.confuciustts_url.text()
        params.save()
        
        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))

        test_btn[tts_type].setText(tr('Testing...'))
        import time
        wk = ListenVoice(parent=winobj,
                         queue_tts=[{"text": '你好啊我的朋友,希望你今天开心！', "role": rolename, "filename": config.TEMP_DIR + f"/{time.time()}-{tts_type}.wav", "tts_type": tts_type}],
                         language="zh",
                         tts_type=tts_type)
        wk.uito.connect(feed)
        wk.start()

    def save():

        index_tts_version = winobj.index_tts_version.currentIndex()
        params["index_tts_version"] = index_tts_version
        params["voxcpmtts_version"] = winobj.voxcpmtts_version.currentText()
        
        params["voxcpmtts_url"] = winobj.voxcpmtts_url.text()
        params["diatts_url"] = winobj.diatts_url.text()
        params["indextts_url"] = winobj.indextts_url.text()
        params["sparktts_url"] = winobj.sparktts_url.text()
        params["f5tts_url"] = winobj.f5tts_url.text()
        params["confuciustts_url"] = winobj.confuciustts_url.text()


        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import F5TTSForm
    Path(ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    winobj = F5TTSForm()
    app_cfg.child_forms['f5tts'] = winobj
    winobj.index_tts_version.setCurrentIndex(int(params.get('index_tts_version',0)))
    winobj.voxcpmtts_version.setCurrentText(params.get('voxcpmtts_version','v2'))
    
    winobj.f5tts_url.setText(params.get('f5tts_url',''))
    winobj.confuciustts_url.setText(params.get('confuciustts_url',''))
    winobj.sparktts_url.setText(params.get('sparktts_url',''))
    winobj.indextts_url.setText(params.get('indextts_url',''))
    winobj.diatts_url.setText(params.get('diatts_url',''))
    winobj.voxcpmtts_url.setText(params.get('voxcpmtts_url',''))

    winobj.save.clicked.connect(save)
    winobj.f5tts_urltest.clicked.connect(lambda: test(tts.F5_TTS))
    winobj.sparktts_urltest.clicked.connect(lambda: test(tts.SPARK_TTS))
    winobj.indextts_urltest.clicked.connect(lambda: test(tts.INDEX_TTS))
    winobj.diatts_urltest.clicked.connect(lambda: test(tts.DIA_TTS))
    winobj.voxcpmtts_urltest.clicked.connect(lambda: test(tts.VOXCPM_TTS))
    winobj.confuciustts_urltest.clicked.connect(lambda: test(tts.CONFUCIUS_TTS))
    winobj.show()
    test_btn={
        tts.F5_TTS:winobj.f5tts_urltest,
        tts.INDEX_TTS:winobj.indextts_urltest,
        tts.SPARK_TTS:winobj.sparktts_urltest,
        tts.DIA_TTS:winobj.diatts_urltest,
        tts.VOXCPM_TTS:winobj.voxcpmtts_urltest,
        tts.CONFUCIUS_TTS:winobj.confuciustts_urltest,
    }
