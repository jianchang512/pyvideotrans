from videotrans.configure import config


# set baidu
def openwin():
    def save_baidu():
        appid = winobj.baidu_appid.text()
        miyue = winobj.baidu_miyue.text()
        config.params["baidu_appid"] = appid
        config.params["baidu_miyue"] = miyue
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import BaiduForm
    winobj = config.child_forms.get('baiduw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = BaiduForm()
    config.child_forms['baiduw'] = winobj
    if config.params["baidu_appid"]:
        winobj.baidu_appid.setText(config.params["baidu_appid"])
    if config.params["baidu_miyue"]:
        winobj.baidu_miyue.setText(config.params["baidu_miyue"])
    winobj.set_badiu.clicked.connect(save_baidu)
    winobj.show()
