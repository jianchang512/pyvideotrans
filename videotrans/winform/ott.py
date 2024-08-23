from videotrans.configure import config


def open():
    def save():
        key = config.ottw.ott_address.text()
        config.params["ott_address"] = key
        config.getset_params(config.params)
        config.ottw.close()

    from videotrans.component import OttForm
    if config.ottw is not None:
        config.ottw.show()
        config.ottw.raise_()
        config.ottw.activateWindow()
        return
    config.ottw = OttForm()
    if config.params["ott_address"]:
        config.ottw.ott_address.setText(config.params["ott_address"])
    config.ottw.set_ott.clicked.connect(save)
    config.ottw.show()
