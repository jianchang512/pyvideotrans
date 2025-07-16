
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
                text = translator.run(translate_type=translator.SILICONFLOW_INDEX, text_list=raw,
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
        key = winobj.guiji_key.text()
        model = winobj.guiji_model.currentText()
        template = winobj.template.toPlainText()



        config.params["guiji_key"] = key

        config.params["guiji_model"] = model
        config.params["guiji_template"] = template

        task = Test(parent=winobj)
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save():
        guiji_key = winobj.guiji_key.text()
        template = winobj.template.toPlainText()
        model = winobj.guiji_model.currentText()
        with Path(tools.get_prompt_file('zhipuai')).open('w', encoding='utf-8') as f:
            f.write(template)
        config.params["guiji_key"] = guiji_key
        config.params["guiji_model"] = model
        config.params["guiji_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.guiji_model.currentText()
        winobj.guiji_model.clear()
        winobj.guiji_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.guiji_model.setCurrentText(current_text)
        config.settings['zhipuai_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['guiji_model']
        allmodels = config.settings['guiji_model'].split(',')
        winobj.guiji_model.clear()
        winobj.guiji_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["guiji_key"]:
            winobj.guiji_key.setText(config.params["guiji_key"])
        if config.params["guiji_model"]:
            winobj.guiji_model.setCurrentText(config.params["guiji_model"])
        if config.params["guiji_template"]:
            winobj.template.setPlainText(config.params["guiji_template"])

    from videotrans.component import SiliconflowForm
    winobj = config.child_forms.get('siliconfloww')
    config.params["guiji_template"]=tools.get_prompt('zhipuai')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = SiliconflowForm()
    config.child_forms['siliconfloww'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.test.clicked.connect(test)
    winobj.show()
