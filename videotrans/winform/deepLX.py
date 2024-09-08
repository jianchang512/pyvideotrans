from videotrans.configure import config


def openwin():
    def save():
        key = winobj.deeplx_address.text()
        config.params["deeplx_address"] = key
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
    winobj.set_deeplx.clicked.connect(save)
    winobj.show()
