from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import recognition
from videotrans.configure import config
from videotrans.util import tools


def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                config.box_recogn = 'ing'
                res = recognition.run(
                    audio_file=config.ROOT_DIR + '/videotrans/styles/no-remove.mp3',
                    cache_folder=config.SYS_TMP,
                    recogn_type=recognition.Deepgram,
                    model_name="whisper-large",
                    detect_language="zh-CN"
                )
                srt_str = tools.get_srt_from_list(res)
                self.uito.emit(f"ok:{srt_str}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok",d[3:])
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                           '必须填写 API Key' if config.defaulelang == 'zh' else 'Must fill in the API Key')
            return
        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
        task = Test(parent=winobj)
        winobj.test.setText('测试...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        apikey = winobj.apikey.text().strip()
        utt = winobj.utt.text().strip()
        if not apikey:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                           '必须填写 API Key' if config.defaulelang == 'zh' else 'Must fill in the API Key')
            return
            
        config.params["deepgram_apikey"] = apikey
        config.params["deepgram_utt"] = 200 if utt else 200
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepgramForm
    winobj = config.child_forms.get('deepgramw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepgramForm()
    config.child_forms['deepgramw'] = winobj
    if config.params["deepgram_apikey"]:
        winobj.apikey.setText(config.params["deepgram_apikey"])
    if config.params["deepgram_utt"]:
        winobj.utt.setText(str(config.params["deepgram_utt"]))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
