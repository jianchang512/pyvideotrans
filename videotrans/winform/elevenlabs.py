

def openwin():
    from PySide6.QtCore import QThread, Signal
    from elevenlabs.core import ApiError

    from videotrans.util.help_role import update_elevenlabs_role
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.constants import LISTEN_TEXT
    from videotrans.util.help_misc import set_process, show_error
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,params
    from videotrans.configure import config
    from videotrans.util.ListenVoice import ListenVoice


    winobj = get_cls(Path(__file__).stem)()

    class _UpdateRole(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                update_elevenlabs_role()
                self.uito.emit("ok")
            except ApiError as e:
                self.uito.emit(e.body)
            except Exception as e:
                self.uito.emit(str(e))


    def feed(d):
        if not d.startswith("ok"):
            show_error(d)
        winobj.test.setText(tr("Test"))
        winobj.update_btn.setText(tr('Test & update role'))

    def _update():
        wk=_UpdateRole(parent=winobj)
        wk.uito.connect(feed)
        wk.start()
        winobj.update_btn.setText('Updating...')

    def test():
        params['elevenlabstts_key'] = winobj.elevenlabstts_key.text().strip()
        try:
            from videotrans import tts
            from videotrans.task.simple_runnable_qt import run_in_threadpool
            import json, time
            with open(ROOT_DIR+'/videotrans/voicejson/elevenlabs.json','r',encoding='utf-8') as f:
                jsondata=json.loads(f.read())
            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text":  LISTEN_TEXT.get('en'),
                "role": list(jsondata.keys())[0],
                "filename": config.TEMP_DIR + f"/{time.time()}-elevenlabs.wav",
                "tts_type": tts.ELEVENLABS_TTS}],
                             language="en",
                             tts_type=tts.ELEVENLABS_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText(tr("Testing..."))
        except Exception as e:
            from videotrans.configure.excepts import get_msg_from_except
            show_error(get_msg_from_except(e))



    def save():
        params['elevenlabstts_key'] = winobj.elevenlabstts_key.text().strip()
        params['elevenlabstts_models'] = winobj.elevenlabstts_models.currentText()
        params.save()
        set_process(text='', type="refreshtts")
        set_process(text='', type="refreshmodel_list")
        winobj.close()

    winobj.elevenlabstts_key.setText(str(params.get('elevenlabstts_key','')))
    winobj.elevenlabstts_models.setCurrentText(params.get('elevenlabstts_models',''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.update_btn.clicked.connect(_update)
    return winobj
