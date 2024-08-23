from videotrans.configure import config


def open():
    def save():
        key = config.elevenlabsw.elevenlabstts_key.text()
        config.params['elevenlabstts_key'] = key
        config.getset_params(config.params)
        config.elevenlabsw.close()

    from videotrans.component import ElevenlabsForm
    if config.elevenlabsw is not None:
        config.elevenlabsw.show()
        config.elevenlabsw.raise_()
        config.elevenlabsw.activateWindow()
        return
    config.elevenlabsw = ElevenlabsForm()
    if config.params['elevenlabstts_key']:
        config.elevenlabsw.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
    config.elevenlabsw.set.clicked.connect(save)
    config.elevenlabsw.show()
