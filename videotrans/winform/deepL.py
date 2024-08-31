from videotrans.configure import config


# 翻译

# set deepl key
def open():
    def save():
        key = deeplw.deepl_authkey.text()
        api = deeplw.deepl_api.text().strip()
        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.getset_params(config.params)
        deeplw.close()

    from videotrans.component import DeepLForm
    deeplw = config.child_forms.get('deeplw')
    if deeplw is not None:
        deeplw.show()
        deeplw.raise_()
        deeplw.activateWindow()
        return
    deeplw = DeepLForm()
    config.child_forms['deeplw'] = deeplw
    if config.params['deepl_authkey']:
        deeplw.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        deeplw.deepl_api.setText(config.params['deepl_api'])
    deeplw.set_deepl.clicked.connect(save)
    deeplw.show()
