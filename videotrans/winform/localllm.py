import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
import builtins
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
            QtWidgets.QMessageBox.critical(config.llmw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(config.llmw, "OK", d[3:])
        config.llmw.test_localllm.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = config.llmw.localllm_key.text()
        api = config.llmw.localllm_api.text().strip()
        if not api:
            return QtWidgets.QMessageBox.critical(config.llmw, config.transobj['anerror'],
                                                  '必须填写api地址' if config.defaulelang == 'zh' else 'Please input LLM API url')

        model = config.llmw.localllm_model.currentText()
        template = config.llmw.localllm_template.toPlainText()

        config.params["localllm_key"] = key
        config.params["localllm_api"] = api
        config.params["localllm_model"] = model
        config.params["localllm_template"] = template

        task = TestLocalLLM(parent=config.llmw)
        config.llmw.test_localllm.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save_localllm():
        key = config.llmw.localllm_key.text()
        api = config.llmw.localllm_api.text().strip()

        model = config.llmw.localllm_model.currentText()
        template = config.llmw.localllm_template.toPlainText()

        config.params["localllm_key"] = key
        config.params["localllm_api"] = api
        config.params["localllm_model"] = model
        config.params["localllm_template"] = template
        with builtin_open(config.rootdir + f"/videotrans/localllm{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                  encoding='utf-8') as f:
            f.write(template)
        config.getset_params(config.params)
        config.llmw.close()

    def setallmodels():
        t = config.llmw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.llmw.localllm_model.currentText()
        config.llmw.localllm_model.clear()
        config.llmw.localllm_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.llmw.localllm_model.setCurrentText(current_text)
        config.settings['localllm_model'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import LocalLLMForm
    if config.llmw is not None:
        config.llmw.show()
        config.llmw.raise_()
        config.llmw.activateWindow()
        return
    config.llmw = LocalLLMForm()
    allmodels_str = config.settings['localllm_model']
    allmodels = config.settings['localllm_model'].split(',')
    config.llmw.localllm_model.clear()
    config.llmw.localllm_model.addItems(allmodels)
    config.llmw.edit_allmodels.setPlainText(allmodels_str)
    if config.params["localllm_key"]:
        config.llmw.localllm_key.setText(config.params["localllm_key"])
    if config.params["localllm_api"]:
        config.llmw.localllm_api.setText(config.params["localllm_api"])
    if config.params["localllm_model"] and config.params["localllm_model"] in allmodels:
        config.llmw.localllm_model.setCurrentText(config.params["localllm_model"])
    if config.params["localllm_template"]:
        config.llmw.localllm_template.setPlainText(config.params["localllm_template"])
    config.llmw.edit_allmodels.textChanged.connect(setallmodels)
    config.llmw.set_localllm.clicked.connect(save_localllm)
    config.llmw.test_localllm.clicked.connect(test)
    config.llmw.show()
