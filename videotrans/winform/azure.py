def openwin():
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger

    def save():
        key = winobj.azure_key.text()
        api = winobj.azure_api.text()
        model = winobj.azure_model.currentText()
        version = winobj.azure_version.currentText()

        params["azure_key"] = key
        params["azure_api"] = api
        params["azure_version"] = version
        params["azure_model"] = model

        params.save()

        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.azure_model.currentText()
        winobj.azure_model.clear()

        winobj.azure_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.azure_model.setCurrentText(current_text)
        settings['azure_model'] = t
        settings.save()



    from videotrans.component.set_form import AzureForm

    winobj = AzureForm()
    app_cfg.child_forms['azure'] = winobj
    winobj.update_ui()

    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_azure.clicked.connect(save)
    winobj.show()
