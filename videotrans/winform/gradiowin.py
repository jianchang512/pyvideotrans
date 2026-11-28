

def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.constants import LISTEN_TEXT
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.util.help_role import get_f5tts_role
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg, params
    from videotrans.configure import config
    from pathlib import Path

    from PySide6 import QtWidgets
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans import tts
    from videotrans.tts._index_emotion import (
        parse_emo_vector,
        parse_emo_weight,
        parse_role_emotions,
    )

    def get_index_emotion():
        try:
            vector = parse_emo_vector(winobj.indextts_emo_vector.text())
            weight = parse_emo_weight(winobj.indextts_emo_weight.text())
            role_emotions = winobj.indextts_role_emotions.toPlainText().rstrip()
            parse_role_emotions(role_emotions, weight)
        except ValueError as e:
            show_error(str(e))
            return None
        vector_text = "" if vector is None else ",".join(str(value) for value in vector)
        winobj.indextts_emo_vector.setText(vector_text)
        winobj.indextts_emo_weight.setText(str(weight))
        return vector_text, weight, role_emotions
    

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "Ok", "Test Ok")
        else:
            show_error(d)

        for it in test_btn.values():
            it.setText(tr('Test'))


    def test(tts_type=tts.INDEX_TTS):
        emotion = None
        if tts_type == tts.INDEX_TTS:
            emotion = get_index_emotion()
            if emotion is None:
                return
        indexttsversion = winobj.indextts_version.currentIndex()
        # 通用
        params["index_version"] = indexttsversion
        params["voxcpm_version"] = winobj.voxcpmtts_version.currentText()
        params["voxcpm_url"] = winobj.voxcpmtts_url.text()
        params["firered3tts_url"] = winobj.firered3tts_url.text()
        params["index_url"] = winobj.indextts_url.text()
        if emotion is not None:
            (
                params["index_emo_vector"],
                params["index_emo_weight"],
                params["index_role_emotions"],
            ) = emotion
        params["spark_url"] = winobj.sparktts_url.text()
        params.save()
        
        _rolename = next(reversed(get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return show_error(tr("No reference audio {} exists",file))

        test_btn[tts_type].setText(tr('Testing...'))
        import time
        wk = ListenVoice(parent=winobj,
                         queue_tts=[{"text":  LISTEN_TEXT.get('zh'), "role": rolename, "filename": config.TEMP_DIR + f"/{time.time()}-{tts_type}.wav", "tts_type": tts_type}],
                         language="zh",
                         tts_type=tts_type)
        wk.uito.connect(feed)
        wk.start()

    def save():
        emotion = get_index_emotion()
        if emotion is None:
            return
        indextts_version = winobj.indextts_version.currentIndex()
        params["index_version"] = indextts_version
        params["voxcpm_version"] = winobj.voxcpmtts_version.currentText()
        
        params["voxcpm_url"] = winobj.voxcpmtts_url.text()
        params["firered3tts_url"] = winobj.firered3tts_url.text()
        params["index_url"] = winobj.indextts_url.text()
        (
            params["index_emo_vector"],
            params["index_emo_weight"],
            params["index_role_emotions"],
        ) = emotion
        params["spark_url"] = winobj.sparktts_url.text()


        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()


    Path(ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    winobj = get_cls(Path(__file__).stem)()

    winobj.indextts_version.setCurrentIndex(int(params.get('index_version',0)))
    winobj.voxcpmtts_version.setCurrentText(str(params.get('voxcpm_version','v2')))
    
    winobj.sparktts_url.setText(str(params.get('spark_url','')))
    winobj.indextts_url.setText(str(params.get('index_url','')))
    winobj.indextts_emo_vector.setText(str(params.get('index_emo_vector','')))
    winobj.indextts_emo_weight.setText(str(params.get('index_emo_weight',0.65)))
    winobj.indextts_role_emotions.setPlainText(str(params.get('index_role_emotions','')))
    winobj.voxcpmtts_url.setText(str(params.get('voxcpm_url','')))
    winobj.firered3tts_url.setText(str(params.get('firered3tts_url','')))

    winobj.save.clicked.connect(save)
    winobj.sparktts_urltest.clicked.connect(lambda: test(tts.SPARK_TTS))
    winobj.indextts_urltest.clicked.connect(lambda: test(tts.INDEX_TTS))
    winobj.voxcpmtts_urltest.clicked.connect(lambda: test(tts.VOXCPM_TTS))
    winobj.firered3tts_urltest.clicked.connect(lambda: test(tts.FIRERED3_TTS))
    test_btn={
        tts.INDEX_TTS:winobj.indextts_urltest,
        tts.SPARK_TTS:winobj.sparktts_urltest,
        tts.VOXCPM_TTS:winobj.voxcpmtts_urltest,
        tts.FIRERED3_TTS:winobj.firered3tts_urltest,
    }
    return winobj
