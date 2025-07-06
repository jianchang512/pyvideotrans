from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config
from videotrans.util import tools
from pathlib import Path


def openwin():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None, language=None, role=None):
            super().__init__(parent=parent)
            self.text = text
            self.language = language
            self.role = role
            self.send_error=False

        def run(self):
            try:
                tts.run(
                    queue_tts=[{
                        "text": self.text, "role": self.role,
                                "filename": config.TEMP_HOME + "/testchatterboxtts.mp3", "tts_type": tts.CHATTERBOX_TTS}],
                    language=self.language,
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                if not self.send_error:
                    print(e)
                    self.uito.emit(str(e))
                    self.send_error=True

    def feed(d):
        print(f'{d=}')
        if d == "ok":
            tools.set_process(text='chatterbox', type="refreshtts")
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        winobj.test.setText('Test')

    def test():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url    
        config.params["chatterbox_url"] = url
        config.params["chatterbox_role"] = winobj.role.toPlainText().strip()
        config.params["chatterbox_cfg_weight"]=min( max( float(winobj.cfg_weight.text()),0.0) ,1.0)
        config.params["chatterbox_exaggeration"]=min(  max(float(winobj.exaggeration.text()),0.25),2.0)

        task = TestTTS(parent=winobj,
                       text="Hello,my friend,welcom to China",
                       role=getrole(),
                       language="en")
        winobj.test.setText('Testing...')
        config.getset_params(config.params)
        
        task.uito.connect(feed)
        task.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip()
            if not Path(config.ROOT_DIR+f"/chatterbox/{s}").exists():
                QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                               f"请确保 chatterbox 文件夹内存在音频文件 {s}" if config.defaulelang=='zh' else f'Please make sure that the audio file {s} exists in the chatterbox folder')
                return
            
            role = s

        return role

    def save():
        url = winobj.api_url.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url

        role = winobj.role.toPlainText().strip()

        config.params["chatterbox_url"] = url
        config.params["chatterbox_role"] = role

        
        config.params["chatterbox_cfg_weight"]=min( max( float(winobj.cfg_weight.text()),0.0) ,1.0)
        config.params["chatterbox_exaggeration"]=min(  max(float(winobj.exaggeration.text()),0.25),2.0)
        
        config.getset_params(config.params)
        tools.set_process(text='chatterbox', type="refreshtts")

        winobj.close()

    from videotrans.component import ChatterboxForm
    winobj = config.child_forms.get('chatterboxw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatterboxForm()
    config.child_forms['chatterboxw'] = winobj
    if config.params["chatterbox_url"]:
        winobj.api_url.setText(config.params["chatterbox_url"])
    if config.params["chatterbox_role"]:
        winobj.role.setPlainText(config.params["chatterbox_role"])
    if config.params["chatterbox_cfg_weight"]:
        winobj.cfg_weight.setText(str(config.params["chatterbox_cfg_weight"]))
    if config.params["chatterbox_exaggeration"]:
        winobj.exaggeration.setText(str(config.params["chatterbox_exaggeration"]))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
