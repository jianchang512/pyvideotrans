from videotrans.configure import config


# set baidu
def open():
    def save_baidu():
        appid = config.baiduw.baidu_appid.text()
        miyue = config.baiduw.baidu_miyue.text()
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue
        config.getset_params(config.params)
        config.baiduw.close()

    from videotrans.component import BaiduForm
    if config.baiduw is not None:
        config.baiduw.show()
        config.baiduw.raise_()
        config.baiduw.activateWindow()
        return
    config.baiduw = BaiduForm()
    if config.params["baidu_appid"]:
        config.baiduw.baidu_appid.setText(config.params["baidu_appid"])
    if config.params["baidu_miyue"]:
        config.baiduw.baidu_miyue.setText(config.params["baidu_miyue"])
    config.baiduw.set_badiu.clicked.connect(save_baidu)
    config.baiduw.show()
