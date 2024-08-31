import builtins
import json
import os

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    def save():
        key = geminiw.gemini_key.text()
        model = geminiw.model.currentText()
        template = geminiw.gemini_template.toPlainText()
        os.environ['GOOGLE_API_KEY'] = key
        config.params["gemini_model"] = model
        config.params["gemini_key"] = key
        config.params["gemini_template"] = template
        with builtin_open(config.ROOT_DIR + f"/videotrans/gemini{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                          encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)
        geminiw.close()

    def setallmodels():
        t = geminiw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = geminiw.model.currentText()
        geminiw.model.clear()
        geminiw.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            geminiw.model.setCurrentText(current_text)
        config.settings['gemini_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['gemini_model']
        allmodels = config.settings['gemini_model'].split(',')
        geminiw.model.clear()
        geminiw.model.addItems(allmodels)
        geminiw.edit_allmodels.setPlainText(allmodels_str)
        if config.params["gemini_key"]:
            geminiw.gemini_key.setText(config.params["gemini_key"])
        if config.params["gemini_model"]:
            geminiw.model.setCurrentText(config.params["gemini_model"])
        if config.params["gemini_template"]:
            geminiw.gemini_template.setPlainText(config.params["gemini_template"])

    from videotrans.component import GeminiForm
    geminiw = config.child_forms.get('geminiw')
    if geminiw is not None:
        geminiw.show()
        update_ui()
        geminiw.raise_()
        geminiw.activateWindow()
        return
    geminiw = GeminiForm()
    config.child_forms['geminiw'] = geminiw
    update_ui()
    geminiw.set_gemini.clicked.connect(save)
    geminiw.edit_allmodels.textChanged.connect(setallmodels)
    geminiw.show()
