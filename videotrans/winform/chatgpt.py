import json
import os

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


# set chatgpt
def open():
    class TestChatgpt(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                from videotrans.translator.chatgpt import trans as trans_chatgpt
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = trans_chatgpt(raw, "English" if config.defaulelang != 'zh' else "Chinese", set_p=False,
                                     is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(config.chatgptw, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(config.chatgptw, "OK", d[3:])
        config.chatgptw.test_chatgpt.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = config.chatgptw.chatgpt_key.text()
        api = config.chatgptw.chatgpt_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = config.chatgptw.chatgpt_model.currentText()
        template = config.chatgptw.chatgpt_template.toPlainText()

        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = api
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template

        task = TestChatgpt(parent=config.chatgptw)
        config.chatgptw.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        config.chatgptw.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_chatgpt():
        key = config.chatgptw.chatgpt_key.text()
        api = config.chatgptw.chatgpt_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = config.chatgptw.chatgpt_model.currentText()
        template = config.chatgptw.chatgpt_template.toPlainText()

        with builtin_open(config.rootdir + f"/videotrans/chatgpt{'-en' if config.defaulelang != 'zh' else ''}.txt", 'w',
                  encoding='utf-8') as f:
            f.write(template)
        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = api
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template
        config.getset_params(config.params)
        config.chatgptw.close()

    def setallmodels():
        t = config.chatgptw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.chatgptw.chatgpt_model.currentText()
        config.chatgptw.chatgpt_model.clear()
        config.chatgptw.chatgpt_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.chatgptw.chatgpt_model.setCurrentText(current_text)
        config.settings['chatgpt_model'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import ChatgptForm
    if config.chatgptw is not None:
        config.chatgptw.show()
        config.chatgptw.raise_()
        config.chatgptw.activateWindow()
        return
    config.chatgptw = ChatgptForm()
    allmodels_str = config.settings['chatgpt_model']
    allmodels = config.settings['chatgpt_model'].split(',')
    config.chatgptw.chatgpt_model.clear()
    config.chatgptw.chatgpt_model.addItems(allmodels)
    config.chatgptw.edit_allmodels.setPlainText(allmodels_str)

    if config.params["chatgpt_key"]:
        config.chatgptw.chatgpt_key.setText(config.params["chatgpt_key"])
    if config.params["chatgpt_api"]:
        config.chatgptw.chatgpt_api.setText(config.params["chatgpt_api"])
    if config.params["chatgpt_model"] and config.params['chatgpt_model'] in allmodels:
        config.chatgptw.chatgpt_model.setCurrentText(config.params["chatgpt_model"])
    if config.params["chatgpt_template"]:
        config.chatgptw.chatgpt_template.setPlainText(config.params["chatgpt_template"])

    config.chatgptw.set_chatgpt.clicked.connect(save_chatgpt)
    config.chatgptw.test_chatgpt.clicked.connect(test)
    config.chatgptw.edit_allmodels.textChanged.connect(setallmodels)
    config.chatgptw.show()
