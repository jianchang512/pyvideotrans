import builtins
import json
import webbrowser
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans import translator
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestAI302(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = translator.run(translate_type=translator.AI302_INDEX,text_list=raw, target_language_name="en" if config.defaulelang != 'zh' else "zh",is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(ai302fyw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(ai302fyw, "OK", d[3:])
        ai302fyw.test_ai302.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = ai302fyw.ai302_key.text()
        model = ai302fyw.ai302_model.currentText()
        template = ai302fyw.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template

        task = TestAI302(parent=ai302fyw)
        ai302fyw.test_ai302.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        ai302fyw.test_ai302.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_ai302():
        key = ai302fyw.ai302_key.text()
        model = ai302fyw.ai302_model.currentText()
        template = ai302fyw.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template
        Path(config.ROOT_DIR + f"/videotrans/302ai.txt").write_text(template, encoding='utf-8')
        config.getset_params(config.params)
        ai302fyw.close()

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['ai302_models']
        allmodels = config.settings['ai302_models'].split(',')

        ai302fyw.ai302_model.clear()
        ai302fyw.ai302_model.addItems(allmodels)
        ai302fyw.edit_allmodels.setPlainText(allmodels_str)

        if config.params["ai302_key"]:
            ai302fyw.ai302_key.setText(config.params["ai302_key"])
        if config.params["ai302_model"] and config.params["ai302_model"] in allmodels:
            ai302fyw.ai302_model.setCurrentText(config.params["ai302_model"])
        if config.params["ai302_template"]:
            ai302fyw.ai302_template.setPlainText(config.params["ai302_template"])

    def setallmodels():
        t = ai302fyw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = ai302fyw.ai302_model.currentText()
        ai302fyw.ai302_model.clear()
        ai302fyw.ai302_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            ai302fyw.ai302_model.setCurrentText(current_text)
        config.settings['ai302_models'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import AI302Form
    ai302fyw = config.child_forms.get('ai302fyw')
    if ai302fyw is not None:
        ai302fyw.show()
        update_ui()
        ai302fyw.raise_()
        ai302fyw.activateWindow()
        return
    ai302fyw = AI302Form()
    config.child_forms['ai302fyw'] = ai302fyw
    update_ui()

    ai302fyw.edit_allmodels.textChanged.connect(setallmodels)
    ai302fyw.set_ai302.clicked.connect(save_ai302)
    ai302fyw.test_ai302.clicked.connect(test)
    ai302fyw.label_0.clicked.connect(lambda: webbrowser.open_new_tab("https://302.ai"))
    ai302fyw.label_01.clicked.connect(lambda: webbrowser.open_new_tab("https://pyvideotrans.com/302ai"))
    ai302fyw.show()
