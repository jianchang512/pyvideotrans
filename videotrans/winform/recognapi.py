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
                    recogn_type=recognition.CUSTOM_API,
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
        url = winobj.recognapiform_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)
        
        
        task = Test(parent=winobj)
        winobj.test.setText('测试中...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.recognapiform_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        
        if not url.startswith('http'):
            url='http://'+url
        url = url.rstrip('/')
        key = winobj.recognapiform_key.text().strip()
        config.params["recognapi_url"] = url
        config.params["recognapi_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import RecognAPIForm
    winobj = config.child_forms.get('recognapiw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = RecognAPIForm()
    config.child_forms['recognapiw'] = winobj
    if config.params["recognapi_url"]:
        winobj.recognapiform_address.setText(config.params["recognapi_url"])
    if config.params["recognapi_key"]:
        winobj.recognapiform_key.setText(config.params["recognapi_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
