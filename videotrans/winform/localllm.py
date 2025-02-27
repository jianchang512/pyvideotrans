import json
import os
import re
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config
from videotrans.util import tools


def openwin():
    class TestLocalLLM(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友"
                text = translator.run(translate_type=translator.LOCALLLM_INDEX,
                                      text_list=raw,
                                      target_code="en",
                                      source_code="zh-cn",
                                      is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_localllm.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.localllm_key.text()
        url = winobj.localllm_api.text().strip()
        max_token = winobj.localllm_max_token.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.localllm_model.currentText()
        template = winobj.localllm_template.toPlainText()
        
        temperature = winobj.localllm_temperature.text().strip()
        top_p = winobj.localllm_top_p.text().strip()

        config.params["localllm_temperature"] = temperature
        config.params["localllm_top_p"] = top_p

        config.params["localllm_max_token"] = max_token
        config.params["localllm_key"] = key
        config.params["localllm_api"] = url
        config.params["localllm_model"] = model
        config.params["localllm_template"] = template

        task = TestLocalLLM(parent=winobj)
        winobj.test_localllm.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save_localllm():
        key = winobj.localllm_key.text()
        url = winobj.localllm_api.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.localllm_model.currentText()
        template = winobj.localllm_template.toPlainText()
        max_token = winobj.localllm_max_token.text().strip()
        
        temperature = winobj.localllm_temperature.text().strip()
        top_p = winobj.localllm_top_p.text().strip()
        config.params["localllm_temperature"] = temperature
        config.params["localllm_top_p"] = top_p

        config.params["localllm_key"] = key
        config.params["localllm_api"] = url
        config.params["localllm_max_token"] = max_token

        config.params["localllm_model"] = model
        config.params["localllm_template"] = template
        with Path(tools.get_prompt_file('localllm')).open('w', encoding='utf-8') as f:
            f.write(template)
            f.flush()
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.localllm_model.currentText()
        winobj.localllm_model.clear()
        winobj.localllm_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.localllm_model.setCurrentText(current_text)
        config.settings['localllm_model'] = t
        with  open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['localllm_model']
        allmodels = config.settings['localllm_model'].split(',')
        winobj.localllm_model.clear()
        winobj.localllm_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)
        if config.params["localllm_key"]:
            winobj.localllm_key.setText(config.params["localllm_key"])
        if config.params["localllm_api"]:
            winobj.localllm_api.setText(config.params["localllm_api"])
        if config.params["localllm_model"] and config.params["localllm_model"] in allmodels:
            winobj.localllm_model.setCurrentText(config.params["localllm_model"])
        if config.params["localllm_template"]:
            winobj.localllm_template.setPlainText(config.params["localllm_template"])
        if config.params["localllm_max_token"]:
            winobj.localllm_max_token.setText(str(config.params["localllm_max_token"]))
        if config.params["localllm_temperature"]:
            winobj.localllm_temperature.setText(str(config.params["localllm_temperature"]))
        if config.params["localllm_top_p"]:
            winobj.localllm_top_p.setText(str(config.params["localllm_top_p"]))
            
    from videotrans.component import LocalLLMForm
    winobj = config.child_forms.get('llmw')
    config.params["localllm_template"]=tools.get_prompt('localllm')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = LocalLLMForm()
    config.child_forms['llmw'] = winobj
    update_ui()
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.set_localllm.clicked.connect(save_localllm)
    winobj.test_localllm.clicked.connect(test)
    winobj.show()
