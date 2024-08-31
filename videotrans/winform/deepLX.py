from videotrans.configure import config


def open():
    def save():
        key = deeplxw.deeplx_address.text()
        config.params["deeplx_address"] = key
        config.getset_params(config.params)
        deeplxw.close()

    from videotrans.component import DeepLXForm
    deeplxw = config.child_forms.get('deeplxw')
    if deeplxw is not None:
        deeplxw.show()
        deeplxw.raise_()
        deeplxw.activateWindow()
        return
    deeplxw = DeepLXForm()
    config.child_forms['deeplxw'] = deeplxw
    if config.params["deeplx_address"]:
        deeplxw.deeplx_address.setText(config.params["deeplx_address"])
    deeplxw.set_deeplx.clicked.connect(save)
    deeplxw.show()
