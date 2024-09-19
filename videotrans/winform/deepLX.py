from videotrans.configure import config


def openwin():
    def save():
        url = winobj.deeplx_address.text()
        key = winobj.deeplx_key.text().strip()
        config.params["deeplx_address"] = url
        config.params["deeplx_key"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepLXForm
    winobj = config.child_forms.get('deeplxw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLXForm()
    config.child_forms['deeplxw'] = winobj
    if config.params["deeplx_address"]:
        winobj.deeplx_address.setText(config.params["deeplx_address"])
    if config.params["deeplx_key"]:
        winobj.deeplx_key.setText(config.params["deeplx_key"])
    winobj.set_deeplx.clicked.connect(save)
    winobj.show()
