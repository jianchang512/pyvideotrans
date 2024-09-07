from videotrans.configure import config


def open():
    def save():
        SecretId = winobj.tencent_SecretId.text()
        SecretKey = winobj.tencent_SecretKey.text()
        term = winobj.tencent_term.text().strip()
        config.params["tencent_SecretId"] = SecretId
        config.params["tencent_SecretKey"] = SecretKey
        config.params["tencent_termlist"] = term
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import TencentForm
    winobj = config.child_forms.get('tencentw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = TencentForm()
    config.child_forms['tencentw'] = winobj
    if config.params["tencent_SecretId"]:
        winobj.tencent_SecretId.setText(config.params["tencent_SecretId"])
    if config.params["tencent_SecretKey"]:
        winobj.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
    if config.params["tencent_termlist"]:
        winobj.tencent_term.setText(config.params["tencent_termlist"])
    winobj.set_tencent.clicked.connect(save)
    winobj.show()
