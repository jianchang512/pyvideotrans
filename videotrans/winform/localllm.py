import builtins
import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestLocalLLM(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                from videotrans.translator.localllm import trans as trans_localllm
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = trans_localllm(raw, "English" if config.defaulelang != 'zh' else "Chinese", set_p=False,
                                      is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(llmw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(llmw, "OK", d[3:])
        llmw.test_localllm.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = llmw.localllm_key.text()
        api = llmw.localllm_api.text().strip()
        if not api:
            return QtWidgets.QMessageBox.critical(llmw, config.transobj['anerror'],
                                                  '必须填写api地址' if config.defaulelang == 'zh' else 'Please input LLM API url')

        model = llmw.localllm_model.currentText()
        template = llmw.localllm_template.toPlainText()

        config.params["localllm_key"] = key
        config.params["localllm_api"] = api
        config.params["localllm_model"] = model
        config.params["localllm_template"] = template

        task = TestLocalLLM(parent=llmw)
        llmw.test_localllm.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save_localllm():
        key = llmw.localllm_key.text()
        api = llmw.localllm_api.text().strip()

        model = llmw.localllm_model.currentText()
        template = llmw.localllm_template.toPlainText()

        config.params["localllm_key"] = key
        config.params["localllm_api"] = api
        config.params["localllm_model"] = model
        config.params["localllm_template"] = template
        with builtin_open(config.ROOT_DIR + f"/videotrans/localllm{'-en' if config.defaulelang != 'zh' else ''}.txt",
                          'w',
                          encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)
        llmw.close()

    def setallmodels():
        t = llmw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = llmw.localllm_model.currentText()
        llmw.localllm_model.clear()
        llmw.localllm_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            llmw.localllm_model.setCurrentText(current_text)
        config.settings['localllm_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['localllm_model']
        allmodels = config.settings['localllm_model'].split(',')
        llmw.localllm_model.clear()
        llmw.localllm_model.addItems(allmodels)
        llmw.edit_allmodels.setPlainText(allmodels_str)
        if config.params["localllm_key"]:
            llmw.localllm_key.setText(config.params["localllm_key"])
        if config.params["localllm_api"]:
            llmw.localllm_api.setText(config.params["localllm_api"])
        if config.params["localllm_model"] and config.params["localllm_model"] in allmodels:
            llmw.localllm_model.setCurrentText(config.params["localllm_model"])
        if config.params["localllm_template"]:
            llmw.localllm_template.setPlainText(config.params["localllm_template"])

    from videotrans.component import LocalLLMForm
    llmw = config.child_forms.get('llmw')
    if llmw is not None:
        llmw.show()
        update_ui()
        llmw.raise_()
        llmw.activateWindow()
        return
    llmw = LocalLLMForm()
    config.child_forms['llmw'] = llmw
    update_ui()
    llmw.edit_allmodels.textChanged.connect(setallmodels)
    llmw.set_localllm.clicked.connect(save_localllm)
    llmw.test_localllm.clicked.connect(test)
    llmw.show()
