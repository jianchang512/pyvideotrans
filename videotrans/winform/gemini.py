import json
import os

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    def save():
        key = config.geminiw.gemini_key.text()
        model = config.geminiw.model.currentText()
        template = config.geminiw.gemini_template.toPlainText()
        os.environ['GOOGLE_API_KEY'] = key
        config.params["gemini_model"] = model
        config.params["gemini_key"] = key
        config.params["gemini_template"] = template
        with builtin_open(config.rootdir + f"/videotrans/gemini{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                  encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)
        config.geminiw.close()

    def setallmodels():
        t = config.geminiw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.geminiw.model.currentText()
        config.geminiw.model.clear()
        config.geminiw.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.geminiw.model.setCurrentText(current_text)
        config.settings['gemini_model'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import GeminiForm
    if config.geminiw is not None:
        config.geminiw.show()
        config.geminiw.raise_()
        config.geminiw.activateWindow()
        return
    config.geminiw = GeminiForm()
    allmodels_str = config.settings['gemini_model']
    allmodels = config.settings['gemini_model'].split(',')
    config.geminiw.model.clear()
    config.geminiw.model.addItems(allmodels)
    config.geminiw.edit_allmodels.setPlainText(allmodels_str)
    if config.params["gemini_key"]:
        config.geminiw.gemini_key.setText(config.params["gemini_key"])
    if config.params["gemini_model"]:
        config.geminiw.model.setCurrentText(config.params["gemini_model"])
    if config.params["gemini_template"]:
        config.geminiw.gemini_template.setPlainText(config.params["gemini_template"])
    config.geminiw.set_gemini.clicked.connect(save)
    config.geminiw.edit_allmodels.textChanged.connect(setallmodels)
    config.geminiw.show()
