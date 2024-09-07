from videotrans.configure import config


# 翻译

# set deepl key
def open():
    def save():
        key = winobj.deepl_authkey.text()
        api = winobj.deepl_api.text().strip()
        gid = winobj.deepl_gid.text().strip()
        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.params['deepl_gid'] = gid
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import DeepLForm
    winobj = config.child_forms.get('deeplw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepLForm()
    config.child_forms['deeplw'] = winobj
    if config.params['deepl_authkey']:
        winobj.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        winobj.deepl_api.setText(config.params['deepl_api'])
    if config.params['deepl_gid']:
        winobj.deepl_gid.setText(config.params['deepl_gid'])
    winobj.set_deepl.clicked.connect(save)
    winobj.show()
