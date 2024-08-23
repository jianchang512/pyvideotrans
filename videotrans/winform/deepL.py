from videotrans.configure import config


# 翻译

# set deepl key
def open():
    def save():
        key = config.deeplw.deepl_authkey.text()
        api = config.deeplw.deepl_api.text().strip()
        config.params['deepl_authkey'] = key
        config.params['deepl_api'] = api
        config.getset_params(config.params)
        config.deeplw.close()

    from videotrans.component import DeepLForm
    if config.deeplw is not None:
        config.deeplw.show()
        config.deeplw.raise_()
        config.deeplw.activateWindow()
        return
    config.deeplw = DeepLForm()
    if config.params['deepl_authkey']:
        config.deeplw.deepl_authkey.setText(config.params['deepl_authkey'])
    if config.params['deepl_api']:
        config.deeplw.deepl_api.setText(config.params['deepl_api'])
    config.deeplw.set_deepl.clicked.connect(save)
    config.deeplw.show()
