def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path
    from videotrans.configure.config import params,app_cfg
    from videotrans.winform._helpers import make_setallmodels


    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()

    def save():
        params["azure_key"] = winobj.azure_key.text().strip()
        params["azure_api"] = winobj.azure_api.text()
        params["azure_version"] = winobj.azure_version.currentText()
        params["azure_model"] = winobj.azure_model.currentText()
        params.save()
        winobj.close()

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'azure_model', 'azure_model'))
    winobj.set_azure.clicked.connect(save)
    return winobj
