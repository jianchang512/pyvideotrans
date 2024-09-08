from videotrans.configure import config


def openwin():
    def save():
        key = winobj.ott_address.text()
        config.params["ott_address"] = key
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import OttForm
    winobj = config.child_forms.get('ottw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = OttForm()
    config.child_forms['ottw'] = winobj
    if config.params["ott_address"]:
        winobj.ott_address.setText(config.params["ott_address"])
    winobj.set_ott.clicked.connect(save)
    winobj.show()
