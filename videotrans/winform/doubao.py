from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import recognition
from videotrans.configure import config
from videotrans.util import tools


def openwin():
    class TestTask(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                config.box_recogn='ing'
                res=recognition.run(
                    audio_file=config.ROOT_DIR+'/videotrans/styles/no-remove.mp3',
                    cache_folder=config.SYS_TMP,
                    recogn_type = recognition.DOUBAO_API,
                    detect_language="zh-cn"
                )
                srt_str=tools.get_srt_from_list(res)
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
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        if not appid or not access:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                          '必须填写 Appid & Access_token')
            return

        task = TestTask(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        if not appid or not access:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                          '必须填写 Appid & Access_token')
            return
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        winobj.close()

    from videotrans.component import DoubaoForm
    winobj = config.child_forms.get('doubaow')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DoubaoForm()
    config.child_forms['doubaow'] = winobj
    if config.params["doubao_appid"]:
        winobj.doubao_appid.setText(config.params["doubao_appid"])
    if config.params["doubao_access"]:
        winobj.doubao_access.setText(config.params["doubao_access"])

    winobj.set_save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
