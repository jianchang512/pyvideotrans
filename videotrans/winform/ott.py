def openwin():
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    def save():
        url = winobj.ott_address.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params["ott_address"] = url
        params.save()
        winobj.close()

    from videotrans.component.set_form import OttForm
    winobj = OttForm()
    app_cfg.child_forms['ott'] = winobj
    winobj.ott_address.setText(params.get("ott_address",''))
    winobj.set_ott.clicked.connect(save)
    winobj.show()
