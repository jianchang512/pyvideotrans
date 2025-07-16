
from pathlib import Path
import json
from videotrans.configure import config
from videotrans.util import tools
from videotrans  import translator
from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal



def openwin():
    class Test(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.DEEPSEEK_INDEX, text_list=raw,
                                      target_code="en",
                                      source_code="zh",
                                      is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.deepseek_key.text()
        model = winobj.deepseek_model.currentText()
        template = winobj.template.toPlainText()



        config.params["deepseek_key"] = key

        config.params["deepseek_model"] = model
        config.params["deepseek_template"] = template

        task = Test(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        deepseek_key = winobj.deepseek_key.text()
        template = winobj.template.toPlainText()
        model = winobj.deepseek_model.currentText()
        with Path(tools.get_prompt_file('deepseek')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["deepseek_key"] = deepseek_key
        config.params["deepseek_model"] = model
        config.params["deepseek_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.deepseek_model.currentText()
        winobj.deepseek_model.clear()
        winobj.deepseek_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.deepseek_model.setCurrentText(current_text)
        config.settings['deepseek_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['deepseek_model']
        allmodels = config.settings['deepseek_model'].split(',')
        winobj.deepseek_model.clear()
        winobj.deepseek_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["deepseek_key"]:
            winobj.deepseek_key.setText(config.params["deepseek_key"])
        if config.params["deepseek_model"]:
            winobj.deepseek_model.setCurrentText(config.params["deepseek_model"])
        if config.params["deepseek_template"]:
            winobj.template.setPlainText(config.params["deepseek_template"])

    from videotrans.component import DeepseekForm
    winobj = config.child_forms.get('deepseekw')
    config.params["deepseek_template"]=tools.get_prompt('deepseek')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = DeepseekForm()
    config.child_forms['deepseekw'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
