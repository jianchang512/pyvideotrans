import json
from pathlib import Path

from videotrans.configure import config
from videotrans.util import tools


def openwin():
    def save():
        key = winobj.azure_key.text()
        api = winobj.azure_api.text()
        model = winobj.azure_model.currentText()
        version = winobj.azure_version.currentText()
        template = winobj.azure_template.toPlainText()

        config.params["azure_key"] = key
        config.params["azure_api"] = api
        config.params["azure_version"] = version
        config.params["azure_model"] = model
        config.params["azure_template"] = template

        with Path(tools.get_prompt_file('azure')).open('w', encoding='utf-8') as f:
            f.write(template)
            f.flush()
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

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['azure_model']
        allmodels = config.settings['azure_model'].split(',')
        winobj.azure_model.clear()
        winobj.azure_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["azure_key"]:
            winobj.azure_key.setText(config.params["azure_key"])
        if config.params["azure_api"]:
            winobj.azure_api.setText(config.params["azure_api"])
        if config.params["azure_version"]:
            winobj.azure_version.setCurrentText(config.params["azure_version"])
        if config.params["azure_model"] and config.params['azure_model'] in allmodels:
            winobj.azure_model.setCurrentText(config.params["azure_model"])
        if config.params["azure_template"]:
            winobj.azure_template.setPlainText(config.params["azure_template"])

    from videotrans.component import AzureForm
    winobj = config.child_forms.get('azurew')
    config.params["azure_template"]=tools.get_prompt('azure')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AzureForm()
    config.child_forms['azurew'] = winobj
    update_ui()

    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_azure.clicked.connect(save)
    winobj.show()
