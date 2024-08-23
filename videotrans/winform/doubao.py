from videotrans.configure import config


def open():
    def save():
        appid = config.doubaow.doubao_appid.text()

        access = config.doubaow.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        config.doubaow.close()

    from videotrans.component import DoubaoForm
    if config.doubaow is not None:
        config.doubaow.show()
        config.doubaow.raise_()
        config.doubaow.activateWindow()
        return
    config.doubaow = DoubaoForm()
    if config.params["doubao_appid"]:
        config.doubaow.doubao_appid.setText(config.params["doubao_appid"])
    if config.params["doubao_access"]:
        config.doubaow.doubao_access.setText(config.params["doubao_access"])

    config.doubaow.set_save.clicked.connect(save)
    config.doubaow.show()
