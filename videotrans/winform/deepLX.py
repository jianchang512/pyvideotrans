from videotrans.configure import config


def open():
    def save():
        key = config.deeplxw.deeplx_address.text()
        config.params["deeplx_address"] = key
        config.getset_params(config.params)
        config.deeplxw.close()

    from videotrans.component import DeepLXForm
    if config.deeplxw is not None:
        config.deeplxw.show()
        config.deeplxw.raise_()
        config.deeplxw.activateWindow()
        return
    config.deeplxw = DeepLXForm()
    if config.params["deeplx_address"]:
        config.deeplxw.deeplx_address.setText(config.params["deeplx_address"])
    config.deeplxw.set_deeplx.clicked.connect(save)
    config.deeplxw.show()
