from videotrans.configure import config


def openwin():
    def save():
        appid = winobj.doubao_appid.text()

        access = winobj.doubao_access.text()
        config.params["doubao_appid"] = appid
        config.params["doubao_access"] = access
        config.getset_params(config.params)

        winobj.close()

    from videotrans.component import DoubaoForm
    winobj = config.child_forms.get('doubaow')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DoubaoForm()
    config.child_forms['doubaow'] = winobj
    if config.params["doubao_appid"]:
        winobj.doubao_appid.setText(config.params["doubao_appid"])
    if config.params["doubao_access"]:
        winobj.doubao_access.setText(config.params["doubao_access"])

    winobj.set_save.clicked.connect(save)
    winobj.show()
