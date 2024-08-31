from videotrans.configure import config


def open():
    def save():
        key = elevenlabsw.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key
        config.getset_params(config.params)
        elevenlabsw.close()

    from videotrans.component import ElevenlabsForm
    elevenlabsw = config.child_forms.get('elevenlabsw')
    if elevenlabsw is not None:
        elevenlabsw.show()
        elevenlabsw.raise_()
        elevenlabsw.activateWindow()
        return
    elevenlabsw = ElevenlabsForm()
    config.child_forms['elevenlabsw'] = elevenlabsw
    if config.params['elevenlabstts_key']:
        elevenlabsw.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
    elevenlabsw.set.clicked.connect(save)
    elevenlabsw.show()
