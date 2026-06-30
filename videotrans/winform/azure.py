def openwin():
    from videotrans.configure.config import params,app_cfg
    from videotrans.winform._helpers import make_setallmodels
    from videotrans.component.set_form import AzureForm

    winobj = AzureForm()
    app_cfg.child_forms['azure'] = winobj
    winobj.update_ui()

    def save():
        params["azure_key"] = winobj.azure_key.text()
        params["azure_api"] = winobj.azure_api.text()
        params["azure_version"] = winobj.azure_version.currentText()
        params["azure_model"] = winobj.azure_model.currentText()
        params.save()
        winobj.close()

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'azure_model', 'azure_model'))
    winobj.set_azure.clicked.connect(save)
    winobj.show()
