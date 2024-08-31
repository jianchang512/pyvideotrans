from videotrans.configure import config


def open():
    def save():
        key = ottw.ott_address.text()
        config.params["ott_address"] = key
        config.getset_params(config.params)
        ottw.close()

    from videotrans.component import OttForm
    ottw = config.child_forms.get('ottw')
    if ottw is not None:
        ottw.show()
        ottw.raise_()
        ottw.activateWindow()
        return
    ottw = OttForm()
    config.child_forms['ottw'] = ottw
    if config.params["ott_address"]:
        ottw.ott_address.setText(config.params["ott_address"])
    ottw.set_ott.clicked.connect(save)
    ottw.show()
