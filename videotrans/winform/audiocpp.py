

def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.constants import LISTEN_TEXT
    from videotrans.util.help_misc import show_error
    from videotrans.util.help_role import get_f5tts_role
    from pathlib import Path
    from videotrans.configure.config import ROOT_DIR,tr,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice
    import json

    winobj = get_cls(Path(__file__).stem)()
    jsondata=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/audiocpp.json').read_text(encoding="utf-8"))


    def feed(d):
        if d == "ok":
            from PySide6 import QtWidgets
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            show_error(d)
        winobj.test.setText(tr('Test'))

    def test():
        params["audiocpp_model"] = winobj.model.currentText()
        params.save()
        _rolename = next(reversed(get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=f'{ROOT_DIR}/f5-tts/{rolename}'
        if not Path(file).exists():
            return show_error(tr("No reference audio {} exists",file))
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text":  LISTEN_TEXT.get('en'),
            "role": rolename,
            "filename": f"{config.TEMP_DIR}/test-chatterbox.wav",
            "tts_type": tts.AUDIOCPP_TTS}], language="en",
            tts_type=tts.AUDIOCPP_TTS)
        wk.uito.connect(feed)
        wk.start()

    def save():
        params["audiocpp_model"] = winobj.model.currentText()
        params.save()
        winobj.close()

    def change_model(model_name):
        support_languages=jsondata.get(model_name,{}).get('support_languages')
        if support_languages:
            winobj.loglable.setText( f"{model_name} {tr('Only support')} "+(",".join([tr(code) for code in support_languages])))
        else:
            winobj.loglable.setText('')


    winobj.model.currentTextChanged.connect(change_model)
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    return winobj
