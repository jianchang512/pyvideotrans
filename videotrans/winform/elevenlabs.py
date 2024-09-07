from videotrans.configure import config


def open():
    def save():
        key = winobj.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key
        config.getset_params(config.params)
        winobj.close()

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
    winobj.show()
