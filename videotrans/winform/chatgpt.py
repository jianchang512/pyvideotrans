import json
import os

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config


# set chatgpt
def openwin():
    class TestChatgpt(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = translator.run(translate_type=translator.CHATGPT_INDEX, text_list=raw,
                                      target_language_name="en" if config.defaulelang != 'zh' else "zh", is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_chatgpt.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        key = winobj.chatgpt_key.text()
        api = winobj.chatgpt_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = winobj.chatgpt_model.currentText()
        template = winobj.chatgpt_template.toPlainText()

        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = api
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template

        task = TestChatgpt(parent=winobj)
        winobj.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()
        winobj.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')

    def save_chatgpt():
        key = winobj.chatgpt_key.text()
        api = winobj.chatgpt_api.text().strip()
        api = api if api else 'https://api.openai.com/v1'
        model = winobj.chatgpt_model.currentText()
        template = winobj.chatgpt_template.toPlainText()

        with open(config.ROOT_DIR + f"/videotrans/chatgpt{'-en' if config.defaulelang != 'zh' else ''}.txt",
                  'w',
                  encoding='utf-8') as f:
            f.write(template)
        os.environ['OPENAI_API_KEY'] = key
        config.params["chatgpt_key"] = key
        config.params["chatgpt_api"] = api
        config.params["chatgpt_model"] = model
        config.params["chatgpt_template"] = template
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.chatgpt_model.currentText()
        winobj.chatgpt_model.clear()
        winobj.chatgpt_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.chatgpt_model.setCurrentText(current_text)
        config.settings['chatgpt_model'] = t
        json.dump(config.settings, open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['chatgpt_model']
        allmodels = config.settings['chatgpt_model'].split(',')
        winobj.chatgpt_model.clear()
        winobj.chatgpt_model.addItems(allmodels)
        winobj.edit_allmodels.setPlainText(allmodels_str)

        if config.params["chatgpt_key"]:
            winobj.chatgpt_key.setText(config.params["chatgpt_key"])
        if config.params["chatgpt_api"]:
            winobj.chatgpt_api.setText(config.params["chatgpt_api"])
        if config.params["chatgpt_model"] and config.params['chatgpt_model'] in allmodels:
            winobj.chatgpt_model.setCurrentText(config.params["chatgpt_model"])
        if config.params["chatgpt_template"]:
            winobj.chatgpt_template.setPlainText(config.params["chatgpt_template"])

    from videotrans.component import ChatgptForm
    winobj = config.child_forms.get('chatgptw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ChatgptForm()
    config.child_forms['chatgptw'] = winobj
    update_ui()
    winobj.set_chatgpt.clicked.connect(save_chatgpt)
    winobj.test_chatgpt.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
