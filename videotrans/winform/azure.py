def openwin():
    import json
    from videotrans.configure import config

    def save():
        key = winobj.azure_key.text()
        api = winobj.azure_api.text()
        model = winobj.azure_model.currentText()
        version = winobj.azure_version.currentText()

        config.params["azure_key"] = key
        config.params["azure_api"] = api
        config.params["azure_version"] = version
        config.params["azure_model"] = model

        config.getset_params(config.params)

        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.azure_model.currentText()
        winobj.azure_model.clear()

        winobj.azure_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.azure_model.setCurrentText(current_text)
        config.settings['azure_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))



    from videotrans.component.set_form import AzureForm

    winobj = AzureForm()
    config.child_forms['azure'] = winobj
    winobj.update_ui()

    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_azure.clicked.connect(save)
    winobj.show()
