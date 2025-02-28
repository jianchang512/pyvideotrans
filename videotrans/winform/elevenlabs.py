from PySide6.QtWidgets import QMessageBox

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal


from videotrans.configure import config
from videotrans.util import tools
from videotrans import tts


def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                tools.get_elevenlabs_role(force=True, raise_exception=True)
                tts.run(
                    queue_tts=[{"text": "Hello my friends.", "role": "Aria",
                                "filename": config.TEMP_HOME + "/testelevlabstts", "tts_type": tts.ELEVENLABS_TTS}],
                    language="en",
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')
    
    def save():
        key = winobj.elevenlabstts_key.text()
        model=winobj.elevenlabstts_models.currentText()
        config.params['elevenlabstts_key'] = key
        config.params['elevenlabstts_models'] = model
        config.getset_params(config.params)
        winobj.close()

    def test():
        key = winobj.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key

        try:
            
            task = Test(parent=winobj)
            winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
            task.uito.connect(feed)
            task.start()
        except Exception as e:
            QMessageBox.critical(winobj, "Error", str(e))


    from videotrans.component import ElevenlabsForm
    winobj = config.child_forms.get('elevenlabsw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ElevenlabsForm()
    config.child_forms['elevenlabsw'] = winobj
    if config.params['elevenlabstts_key']:
        winobj.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
    if config.params['elevenlabstts_models']:
        winobj.elevenlabstts_models.setCurrentText(config.params['elevenlabstts_models'])    
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
