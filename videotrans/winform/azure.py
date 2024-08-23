import json

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    def save():
        key = config.azurew.azure_key.text()
        api = config.azurew.azure_api.text()
        model = config.azurew.azure_model.currentText()
        version = config.azurew.azure_version.currentText()
        template = config.azurew.azure_template.toPlainText()

        config.params["azure_key"] = key
        config.params["azure_api"] = api
        config.params["azure_version"] = version
        config.params["azure_model"] = model
        config.params["azure_template"] = template
        with builtin_open(config.rootdir + f"/videotrans/azure{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                  encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)

        config.azurew.close()

    def setallmodels():
        t = config.azurew.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.azurew.azure_model.currentText()
        config.azurew.azure_model.clear()

        config.azurew.azure_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.azurew.azure_model.setCurrentText(current_text)
        config.settings['azure_model'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import AzureForm
    if config.azurew is not None:
        config.azurew.show()
        config.azurew.raise_()
        config.azurew.activateWindow()
        return
    config.azurew = AzureForm()
    allmodels_str = config.settings['azure_model']
    allmodels = config.settings['azure_model'].split(',')
    config.azurew.azure_model.clear()
    config.azurew.azure_model.addItems(allmodels)
    config.azurew.edit_allmodels.setPlainText(allmodels_str)

    if config.params["azure_key"]:
        config.azurew.azure_key.setText(config.params["azure_key"])
    if config.params["azure_api"]:
        config.azurew.azure_api.setText(config.params["azure_api"])
    if config.params["azure_version"]:
        config.azurew.azure_version.setCurrentText(config.params["azure_version"])
    if config.params["azure_model"] and config.params['azure_model'] in allmodels:
        config.azurew.azure_model.setCurrentText(config.params["azure_model"])
    if config.params["azure_template"]:
        config.azurew.azure_template.setPlainText(config.params["azure_template"])

    config.azurew.edit_allmodels.textChanged.connect(setallmodels)
    config.azurew.set_azure.clicked.connect(save)
    config.azurew.show()
