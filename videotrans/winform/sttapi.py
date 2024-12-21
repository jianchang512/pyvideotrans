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
                    recogn_type=recognition.STT_API,
                    detect_language="zh-cn"
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
        url = winobj.stt_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params['stt_url'] = url
        task = Test(parent=winobj)
        winobj.test.setText('测试...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.stt_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.stt_model.currentText()
        url = url.rstrip('/')
        
        config.params["stt_url"] = url
        config.params["stt_model"] = model
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import SttAPIForm
    winobj = config.child_forms.get('sttw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = SttAPIForm()
    config.child_forms['sttw'] = winobj
    if config.params["stt_url"]:
        winobj.stt_url.setText(config.params["stt_url"])
    if config.params["stt_model"]:
        winobj.stt_model.setCurrentText(config.params["stt_model"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
