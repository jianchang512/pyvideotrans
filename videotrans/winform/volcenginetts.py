import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config


def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            from videotrans.tts import run
            try:
                run(
                    queue_tts=[{"text": self.text, "role": "通用男声", "filename": config.TEMP_HOME + "/testvolcenginetts.mp3",  "tts_type": tts.VOLCENGINE_TTS}],
                    language="zh-CN",
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('测试')

    def test():
        # volcenginetts_appid
        # volcenginetts_access
        # volcenginetts_cluster
        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()
        if not appid or not access or not cluster:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                                  '必须填写 appid access 和 cluster')
        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        task = TestTTS(parent=winobj, text="你好啊我的朋友")
        winobj.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def save():
        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()

        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        config.getset_params(config.params)
        winobj.close()

    def update_ui():

        if config.params["volcenginetts_appid"]:
            winobj.volcenginetts_appid.setText(config.params["volcenginetts_appid"])
        if config.params["volcenginetts_access"]:
            winobj.volcenginetts_access.setText(config.params["volcenginetts_access"])
        if config.params["volcenginetts_cluster"]:
            winobj.volcenginetts_cluster.setText(config.params["volcenginetts_cluster"])

    from videotrans.component import VolcEngineTTSForm
    winobj = config.child_forms.get('volcenginettsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = VolcEngineTTSForm()
    config.child_forms['volcenginettsw'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
