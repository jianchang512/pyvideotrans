def openwin():
    from videotrans.configure import config
    def save():
        url = winobj.ott_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["ott_address"] = url
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import OttForm
    winobj = OttForm()
    config.child_forms['ott'] = winobj
    winobj.ott_address.setText(config.params.get("ott_address",''))
    winobj.set_ott.clicked.connect(save)
    winobj.show()
