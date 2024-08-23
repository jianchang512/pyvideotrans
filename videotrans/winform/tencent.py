from videotrans.configure import config


def open():
    def save():
        SecretId = config.tencentw.tencent_SecretId.text()
        SecretKey = config.tencentw.tencent_SecretKey.text()
        config.params["tencent_SecretId"] = SecretId
        config.params["tencent_SecretKey"] = SecretKey
        config.getset_params(config.params)
        config.tencentw.close()

    from videotrans.component import TencentForm
    if config.tencentw is not None:
        config.tencentw.show()
        config.tencentw.raise_()
        config.tencentw.activateWindow()
        return
    config.tencentw = TencentForm()
    if config.params["tencent_SecretId"]:
        config.tencentw.tencent_SecretId.setText(config.params["tencent_SecretId"])
    if config.params["tencent_SecretKey"]:
        config.tencentw.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
    config.tencentw.set_tencent.clicked.connect(save)
    config.tencentw.show()
