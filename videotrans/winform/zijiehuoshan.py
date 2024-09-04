import builtins
import json
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans import translator
from videotrans.configure import config

# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestZijiehuoshan(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                raw = "你好啊我的朋友" if config.defaulelang != 'zh' else "hello,my friend"
                text = translator.run(translate_type=translator.ZIJIE_INDEX, text_list=raw,
                                      target_language_name="en" if config.defaulelang != 'zh' else "zh", is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(zijiew, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(zijiew, "OK", d[3:])
        zijiew.test_zijiehuoshan.setText('测试')

    def test():
        key = zijiew.zijiehuoshan_key.text()
        model = zijiew.zijiehuoshan_model.currentText()
        if not key or not model.strip():
            return QtWidgets.QMessageBox.critical(zijiew, config.transobj['anerror'], '必须填写API key和推理接入点')

        template = zijiew.zijiehuoshan_template.toPlainText()
        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template

        task = TestZijiehuoshan(parent=zijiew)
        zijiew.test_zijiehuoshan.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save_zijiehuoshan():
        key = zijiew.zijiehuoshan_key.text()

        model = zijiew.zijiehuoshan_model.currentText()
        template = zijiew.zijiehuoshan_template.toPlainText()

        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template
        Path(config.ROOT_DIR + f"/videotrans/zijie.txt").write_text(template, encoding='utf-8')
        config.getset_params(config.params)
        zijiew.close()

    def setallmodels():
        t = zijiew.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        t_list = [x for x in t.split(',') if x.strip()]
        current_text = zijiew.zijiehuoshan_model.currentText()
        zijiew.zijiehuoshan_model.clear()
        zijiew.zijiehuoshan_model.addItems(t_list)
        if current_text:
            zijiew.zijiehuoshan_model.setCurrentText(current_text)
        config.settings['zijiehuoshan_model'] = t
        json.dump(config.settings, builtin_open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8'),
                  ensure_ascii=False)

    def update_ui():
        config.settings = config.parse_init()
        allmodels_str = config.settings['zijiehuoshan_model']
        allmodels = config.settings['zijiehuoshan_model'].split(',')
        zijiew.zijiehuoshan_model.clear()
        zijiew.zijiehuoshan_model.addItems(allmodels)
        zijiew.edit_allmodels.setPlainText(allmodels_str)

        if config.params["zijiehuoshan_key"]:
            zijiew.zijiehuoshan_key.setText(config.params["zijiehuoshan_key"])
        if config.params["zijiehuoshan_model"] and config.params['zijiehuoshan_model'] in allmodels:
            zijiew.zijiehuoshan_model.setCurrentText(config.params["zijiehuoshan_model"])
        if config.params["zijiehuoshan_template"]:
            zijiew.zijiehuoshan_template.setPlainText(config.params["zijiehuoshan_template"])

    from videotrans.component import ZijiehuoshanForm
    zijiew = config.child_forms.get('zijiew')
    if zijiew is not None:
        zijiew.show()
        update_ui()
        zijiew.raise_()
        zijiew.activateWindow()
        return
    zijiew = ZijiehuoshanForm()
    config.child_forms['zijiew'] = zijiew
    update_ui()
    zijiew.edit_allmodels.textChanged.connect(setallmodels)
    zijiew.set_zijiehuoshan.clicked.connect(save_zijiehuoshan)
    zijiew.test_zijiehuoshan.clicked.connect(test)
    zijiew.show()
