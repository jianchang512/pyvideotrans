from videotrans.configure import config


def open():
    def save():
        appid = doubaow.doubao_appid.text()

        access = doubaow.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        doubaow.close()

    from videotrans.component import DoubaoForm
    doubaow = config.child_forms.get('doubaow')
    if doubaow is not None:
        doubaow.show()
        doubaow.raise_()
        doubaow.activateWindow()
        return
    doubaow = DoubaoForm()
    config.child_forms['doubaow'] = doubaow
    if config.params["doubao_appid"]:
        doubaow.doubao_appid.setText(config.params["doubao_appid"])
    if config.params["doubao_access"]:
        doubaow.doubao_access.setText(config.params["doubao_access"])

    doubaow.set_save.clicked.connect(save)
    doubaow.show()
