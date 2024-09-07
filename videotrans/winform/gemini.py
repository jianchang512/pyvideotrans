import builtins
import json
import os

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    def save():
        key = winobj.gemini_key.text()
        model = winobj.model.currentText()
        template = winobj.gemini_template.toPlainText()
        os.environ['GOOGLE_API_KEY'] = key
        config.params["gemini_model"] = model
        config.params["gemini_key"] = key
        config.params["gemini_template"] = template
        with builtin_open(config.ROOT_DIR + f"/videotrans/gemini{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                          encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.model.currentText()
        winobj.model.clear()
        winobj.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.model.setCurrentText(current_text)
        config.settings['gemini_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['gemini_model']
        allmodels = config.settings['gemini_model'].split(',')
        winobj.model.clear()
        winobj.model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)
        if config.params["gemini_key"]:
            winobj.gemini_key.setText(config.params["gemini_key"])
        if config.params["gemini_model"]:
            winobj.model.setCurrentText(config.params["gemini_model"])
        if config.params["gemini_template"]:
            winobj.gemini_template.setPlainText(config.params["gemini_template"])

    from videotrans.component import GeminiForm
    winobj = config.child_forms.get('geminiw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = GeminiForm()
    config.child_forms['geminiw'] = winobj
    update_ui()
    winobj.set_gemini.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
