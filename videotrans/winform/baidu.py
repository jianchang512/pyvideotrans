from videotrans.configure import config


# set baidu
def open():
    def save_baidu():
        appid = baiduw.baidu_appid.text()
        miyue = baiduw.baidu_miyue.text()
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue
        config.getset_params(config.params)
        baiduw.close()

    from videotrans.component import BaiduForm
    baiduw = config.child_forms.get('baiduw')
    if baiduw is not None:
        baiduw.show()
        baiduw.raise_()
        baiduw.activateWindow()
        return
    baiduw = BaiduForm()
    config.child_forms['baiduw'] = baiduw
    if config.params["baidu_appid"]:
        baiduw.baidu_appid.setText(config.params["baidu_appid"])
    if config.params["baidu_miyue"]:
        baiduw.baidu_miyue.setText(config.params["baidu_miyue"])
    baiduw.set_badiu.clicked.connect(save_baidu)
    baiduw.show()
