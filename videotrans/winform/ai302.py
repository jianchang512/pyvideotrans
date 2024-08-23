import json
import webbrowser
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestAI302(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                from videotrans.translator.ai302 import trans as trans_ai302
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = trans_ai302(raw, "English" if config.defaulelang != 'zh' else "Chinese", set_p=False,
                                   is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(config.ai302fyw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(config.ai302fyw, "OK", d[3:])
        config.ai302fyw.test_ai302.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = config.ai302fyw.ai302_key.text()
        model = config.ai302fyw.ai302_model.currentText()
        template = config.ai302fyw.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template

        task = TestAI302(parent=config.ai302fyw)
        config.ai302fyw.test_ai302.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        config.ai302fyw.test_ai302.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_ai302():
        key = config.ai302fyw.ai302_key.text()
        model = config.ai302fyw.ai302_model.currentText()
        template = config.ai302fyw.ai302_template.toPlainText()

        config.params["ai302_key"] = key
        config.params["ai302_model"] = model
        config.params["ai302_template"] = template
        Path(config.rootdir + f"/videotrans/302ai.txt").write_text(template,encoding='utf-8')
        config.getset_params(config.params)
        config.ai302fyw.close()

    def setallmodels():
        t = config.ai302fyw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.ai302fyw.ai302_model.currentText()
        config.ai302fyw.ai302_model.clear()
        config.ai302fyw.ai302_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.ai302fyw.ai302_model.setCurrentText(current_text)
        config.settings['ai302_models'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'), ensure_ascii=False)

    from videotrans.component import AI302Form
    if config.ai302fyw is not None:
        config.ai302fyw.show()
        config.ai302fyw.raise_()
        config.ai302fyw.activateWindow()
        return
    config.ai302fyw = AI302Form()
    allmodels_str = config.settings['ai302_models']
    allmodels = config.settings['ai302_models'].split(',')

    config.ai302fyw.ai302_model.clear()
    config.ai302fyw.ai302_model.addItems(allmodels)
    config.ai302fyw.edit_allmodels.setPlainText(allmodels_str)

    if config.params["ai302_key"]:
        config.ai302fyw.ai302_key.setText(config.params["ai302_key"])
    if config.params["ai302_model"] and config.params["ai302_model"] in allmodels:
        config.ai302fyw.ai302_model.setCurrentText(config.params["ai302_model"])
    if config.params["ai302_template"]:
        config.ai302fyw.ai302_template.setPlainText(config.params["ai302_template"])
    config.ai302fyw.edit_allmodels.textChanged.connect(setallmodels)
    config.ai302fyw.set_ai302.clicked.connect(save_ai302)
    config.ai302fyw.test_ai302.clicked.connect(test)
    config.ai302fyw.label_0.clicked.connect(lambda: webbrowser.open_new_tab("https://302.ai"))
    config.ai302fyw.label_01.clicked.connect(lambda: webbrowser.open_new_tab("https://pyvideotrans.com/302ai"))
    config.ai302fyw.show()
