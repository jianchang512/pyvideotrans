from PySide6.QtWidgets import QMessageBox

from videotrans.configure import config
from videotrans.util import tools


def openwin():
    def save():
        key = winobj.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key
        config.getset_params(config.params)
        winobj.close()

    def test():
        key = winobj.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key

        try:
            tools.get_elevenlabs_role(force=True, raise_exception=True)
        except Exception as e:
            QMessageBox.critical(winobj, "Error", str(e))
        else:
            QMessageBox.information(winobj, "Success", "OK")

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
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
