import json

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestTTS(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, text=None):
            super().__init__(parent=parent)
            self.text = text

        def run(self):
            from videotrans.tts.ai302tts import get_voice
            try:
                role = 'alloy'
                if config.params["ai302tts_model"] == 'doubao':
                    role = 'zh_female_shuangkuaisisi_moon_bigtts'
                elif config.params['ai302tts_model'] == 'azure':
                    role = "zh-CN-YunjianNeural"
                get_voice(
                    text=self.text,
                    role=role,
                    language="zh-CN",
                    rate='+0%',
                    set_p=False, filename=config.homedir + "/test.mp3")
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if d == "ok":
            tools.pygameaudio(config.homedir + "/test.mp3")
            QtWidgets.QMessageBox.information(config.ai302ttsw, "ok", "Test Ok")
        else:
            QtWidgets.QMessageBox.critical(config.ai302ttsw, config.transobj['anerror'], d)
        config.ai302ttsw.test_ai302tts.setText('测试')

    def test():
        key = config.ai302ttsw.ai302tts_key.text().strip()
        model = config.ai302ttsw.ai302tts_model.currentText()
        if not key or not model:
            return QtWidgets.QMessageBox.critical(config.ai302ttsw, config.transobj['anerror'],
                                                  '必须填写 302.ai 的API KEY 和 model')
        config.params["ai302tts_key"] = key
        config.params["ai302tts_model"] = model
        task = TestTTS(parent=config.ai302ttsw, text="你好啊我的朋友")
        config.ai302ttsw.test_ai302tts.setText('测试中请稍等...')
        task.uito.connect(feed)
        task.start()

    def save():
        key = config.ai302ttsw.ai302tts_key.text().strip()
        model = config.ai302ttsw.ai302tts_model.currentText()
        config.params["ai302tts_key"] = key
        config.params["ai302tts_model"] = model
        config.getset_params(config.params)
        config.ai302ttsw.close()

    def setallmodels():
        t = config.ai302ttsw.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = config.ai302ttsw.ai302tts_model.currentText()
        config.ai302ttsw.ai302tts_model.clear()
        config.ai302ttsw.ai302tts_model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            config.ai302ttsw.ai302tts_model.setCurrentText(current_text)
        config.settings['ai302tts_models'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    from videotrans.component import AI302TTSForm
    if config.ai302ttsw is not None:
        config.ai302ttsw.show()
        config.ai302ttsw.raise_()
        config.ai302ttsw.activateWindow()
        return
    config.ai302ttsw = AI302TTSForm()

    allmodels_str = config.settings['ai302tts_models']
    allmodels = config.settings['ai302tts_models'].split(',')
    config.ai302ttsw.ai302tts_model.clear()
    config.ai302ttsw.ai302tts_model.addItems(allmodels)
    config.ai302ttsw.edit_allmodels.setPlainText(allmodels_str)
    if config.params["ai302tts_model"] and config.params["ai302tts_model"] in allmodels:
        config.ai302ttsw.ai302tts_model.setCurrentText(config.params["ai302tts_model"])
    if config.params["ai302tts_key"]:
        config.ai302ttsw.ai302tts_key.setText(config.params["ai302tts_key"])
    config.ai302ttsw.edit_allmodels.textChanged.connect(setallmodels)
    config.ai302ttsw.set_ai302tts.clicked.connect(save)
    config.ai302ttsw.test_ai302tts.clicked.connect(test)
    config.ai302ttsw.show()
