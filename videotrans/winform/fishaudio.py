

def openwin():
    import json
    from PySide6.QtCore import QThread, Signal
    from elevenlabs.core import ApiError

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

        def __init__(self, *, parent=None,api_key=None):
            super().__init__(parent=parent)
            self.api_key=api_key

        def run(self):
            try:
                import requests
                url = f"https://api.fish.audio/model?page_size=100&page_number=1&sort_by=score&self=true&type=tts"
                response = requests.get(url, headers= {"Authorization": f"Bearer {self.api_key}"})
                if response.status_code!=200:
                    self.uito.emit(response.text)
                    return

                data=response.json()
                if not data or data.get('total')<1   or not data.get('items'):
                    self.uito.emit(f'没有自己的声音')
                    return
                results=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/fishaudio.json').read_text(encoding="utf-8"))
                print(f'共 {data["total"]} 个自己的声音')
                for it in data.get('items',[]):
                    # 按照所属语言赋值到第一个
                    if not it.get('languages'):
                        print(f'{it["title"]} 该声音没有语言属性，无法归类，跳过')
                        continue

                    for code in it.get('languages'):
                        if code not in results:
                            results[code]={}
                        results[code]={it['title']:it['_id']}|results[code]

                Path(f'{ROOT_DIR}/videotrans/voicejson/fishaudio.json').write_text( json.dumps(results,ensure_ascii=False,indent=4),encoding="utf-8")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))


    def feed(d):
        if not d.startswith("ok"):
            show_error(d)
        winobj.test.setText(tr("Test"))
        winobj.update_btn.setText(tr('Update my voice'))

    def _update():
        params['fishaudio_key'] = winobj.fishaudio_key.text().strip()
        params['fishaudio_model'] = winobj.fishaudio_model.currentText().strip()
        params.save()
        wk=_UpdateRole(parent=winobj,api_key=params['fishaudio_key'])
        wk.uito.connect(feed)
        wk.start()
        winobj.update_btn.setText('Updating...')

    def test():
        params['fishaudio_key'] = winobj.fishaudio_key.text().strip()
        params['fishaudio_model'] = winobj.fishaudio_model.currentText().strip()
        params.save()
        try:
            from videotrans import tts
            from videotrans.task.simple_runnable_qt import run_in_threadpool
            import json, time
            wk = ListenVoice(parent=winobj, queue_tts=[{
                "text":  LISTEN_TEXT.get('en'),
                "role": "Sarah",
                "filename": config.TEMP_DIR + f"/{time.time()}-fishaudio.wav",
                "tts_type": tts.FISHAUDIOAPI_TTS}],
                             language="en",
                             tts_type=tts.FISHAUDIOAPI_TTS)
            wk.uito.connect(feed)
            wk.start()
            winobj.test.setText(tr("Testing..."))
        except Exception as e:
            from videotrans.configure.excepts import get_msg_from_except
            show_error(get_msg_from_except(e))



    def save():
        params['fishaudio_key'] = winobj.fishaudio_key.text().strip()
        params['fishaudio_model'] = winobj.fishaudio_model.currentText().strip()
        params.save()
        set_process(text='', type="refreshtts")
        winobj.close()

    winobj.fishaudio_key.setText(str(params.get('fishaudio_key','')))
    winobj.fishaudio_model.setCurrentText(params.get('fishaudio_model',''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.update_btn.clicked.connect(_update)
    return winobj
