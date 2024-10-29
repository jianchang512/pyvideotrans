from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools

from pathlib import Path

def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.role = role

        def run(self):
            try:
                config.box_tts='ing'
                tts.run(
                    queue_tts=[{"text": self.text, "role": self.role,
                                "filename": config.TEMP_HOME + "/testf5tts.wav", "tts_type": tts.F5_TTS}],
                    language="zh",
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
        winobj.test.setText('测试api')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.model.currentText()
        role = winobj.role.toPlainText().strip()
        if not role:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], '必须填写参考音频才可测试')
            return
        role_test=getrole()
        if not role_test:
            return
        config.params["f5tts_url"] = url
        config.params["f5tts_model"] = model
        config.params["f5tts_role"] = role
        
        task = TestTTS(parent=winobj,
                       text="你好啊我的朋友",
                       
                       role=role_test)
        winobj.test.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为   音频名称.wav#音频文字内容")
                return
            if not s[0].endswith(".wav"):
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               "每行都必须以#分割为2部分，格式为  音频名称.wav#音频文字内容")
                return
            elif not Path(config.ROOT_DIR+f'/f5-tts/{s[0]}').is_file():
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               f"请将音频文件存放在 {config.ROOT_DIR}/f5-tts 目录下")
                return
            role = s[0]
        config.params['f5tts_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()
        model = winobj.model.currentText()

        config.params["f5tts_url"] = url
        config.params["f5tts_role"] = role
        config.params["f5tts_model"] = model

        config.getset_params(config.params)
        tools.set_process(text='f5tts', type="refreshtts")
        winobj.close()

    from videotrans.component import F5TTSForm
    winobj = config.child_forms.get('f5ttsw')
    Path(config.ROOT_DIR+"/f5-tts").mkdir(exist_ok=True)
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = F5TTSForm()
    config.child_forms['f5ttsw'] = winobj
    if config.params["f5tts_url"]:
        winobj.api_url.setText(config.params["f5tts_url"])
    if config.params["f5tts_role"]:
        winobj.role.setPlainText(config.params["f5tts_role"])
    if config.params["f5tts_model"]:
        winobj.model.setCurrentText(config.params["f5tts_model"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
