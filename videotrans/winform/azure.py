import builtins
import json

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    def save():
        key = azurew.azure_key.text()
        api = azurew.azure_api.text()
        model = azurew.azure_model.currentText()
        version = azurew.azure_version.currentText()
        template = azurew.azure_template.toPlainText()

        config.params["azure_key"] = key
        config.params["azure_api"] = api
        config.params["azure_version"] = version
        config.params["azure_model"] = model
        config.params["azure_template"] = template
        with builtin_open(config.ROOT_DIR + f"/videotrans/azure{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                          encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)

        azurew.close()

    def setallmodels():
        t = azurew.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = azurew.azure_model.currentText()
        azurew.azure_model.clear()

        azurew.azure_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            azurew.azure_model.setCurrentText(current_text)
        config.settings['azure_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['azure_model']
        allmodels = config.settings['azure_model'].split(',')
        azurew.azure_model.clear()
        azurew.azure_model.addItems(allmodels)
        azurew.edit_allmodels.setPlainText(allmodels_str)

        if config.params["azure_key"]:
            azurew.azure_key.setText(config.params["azure_key"])
        if config.params["azure_api"]:
            azurew.azure_api.setText(config.params["azure_api"])
        if config.params["azure_version"]:
            azurew.azure_version.setCurrentText(config.params["azure_version"])
        if config.params["azure_model"] and config.params['azure_model'] in allmodels:
            azurew.azure_model.setCurrentText(config.params["azure_model"])
        if config.params["azure_template"]:
            azurew.azure_template.setPlainText(config.params["azure_template"])

    from videotrans.component import AzureForm
    azurew = config.child_forms.get('azurew')
    if azurew is not None:
        azurew.show()
        update_ui()
        azurew.raise_()
        azurew.activateWindow()
        return
    azurew = AzureForm()
    config.child_forms['azurew'] = azurew
    update_ui()

    azurew.edit_allmodels.textChanged.connect(setallmodels)
    azurew.set_azure.clicked.connect(save)
    azurew.show()
