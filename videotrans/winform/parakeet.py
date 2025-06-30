import json
import os

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import recognition
from videotrans.configure import config


# set chatgpt
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
                    audio_file=config.ROOT_DIR + '/videotrans/styles/no-remove.wav',
                    cache_folder=config.SYS_TMP,
                    recogn_type=recognition.PARAKEET,
                    detect_language="en"
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
        winobj.test.setText(
            '测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.parakeet_address.text().strip().strip('/')
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url=url.replace('/audio/transcriptions','').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url+'/v1'


        config.params["parakeet_address"] = url
        task = Test(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_openairecognapi():
        url = winobj.parakeet_address.text().strip()
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url    
        url=url.replace('/audio/transcriptions','').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url+'/v1'
        


        config.params["parakeet_address"] = url
        config.getset_params(config.params)
        winobj.close()



    def update_ui():
        if config.params["parakeet_address"]:
            winobj.parakeet_address.setText(config.params["parakeet_address"])

    from videotrans.component import ParakeetForm
    winobj = config.child_forms.get('parakeet')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ParakeetForm()
    config.child_forms['parakeet'] = winobj
    update_ui()
    winobj.set_btn.clicked.connect(save_openairecognapi)
    winobj.test.clicked.connect(test)    
    winobj.show()
