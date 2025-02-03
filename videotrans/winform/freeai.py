
from pathlib import Path

from videotrans.configure import config
from videotrans.util import tools



def openwin():

    def save():
        zhipu_key = winobj.zhipu_key.text()
        guiji_key = winobj.guiji_key.text()
        template = winobj.template.toPlainText()
        with Path(tools.get_prompt_file('freeai')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["zhipu_key"] = zhipu_key
        config.params["guiji_key"] = guiji_key
        config.params["freeai_template"] = template
        config.getset_params(config.params)
        winobj.close()


    def update_ui():
        config.settings = config.parse_init()

        if config.params["zhipu_key"]:
            winobj.zhipu_key.setText(config.params["zhipu_key"])
        if config.params["guiji_key"]:
            winobj.guiji_key.setText(config.params["guiji_key"])
        if config.params["freeai_template"]:
            winobj.template.setPlainText(config.params["freeai_template"])

    from videotrans.component import FreeAIForm
    winobj = config.child_forms.get('freeaiw')
    config.params["freeai_template"]=tools.get_prompt('freeai')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = FreeAIForm()
    config.child_forms['freeaiw'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.show()
