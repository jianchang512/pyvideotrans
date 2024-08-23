import json
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


def open():
    class TestZijiehuoshan(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None):
            super().__init__(parent=parent)

        def run(self):
            try:
                from videotrans.translator.huoshan import trans as trans_zijiehuoshan
                raw = "你好啊我的朋友"
                text = trans_zijiehuoshan(raw, "English", set_p=False, is_test=True)
                self.uito.emit(f"ok:{raw}\n{text}")
            except Exception as e:
                self.uito.emit(str(e))

    def feed(d):
        if not d.startswith("ok:"):
            QtWidgets.QMessageBox.critical(config.zijiew, config.transobj['anerror'], d)
        else:
            QtWidgets.QMessageBox.information(config.zijiew, "OK", d[3:])
        config.zijiew.test_zijiehuoshan.setText('测试')

    def test():
        key = config.zijiew.zijiehuoshan_key.text()
        model = config.zijiew.zijiehuoshan_model.currentText()
        if not key or not model.strip():
            return QtWidgets.QMessageBox.critical(config.zijiew, config.transobj['anerror'], '必须填写API key和推理接入点')

        template = config.zijiew.zijiehuoshan_template.toPlainText()
        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template

        task = TestZijiehuoshan(parent=config.zijiew)
        config.zijiew.test_zijiehuoshan.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task.uito.connect(feed)
        task.start()

    def save_zijiehuoshan():
        key = config.zijiew.zijiehuoshan_key.text()

        model = config.zijiew.zijiehuoshan_model.currentText()
        template = config.zijiew.zijiehuoshan_template.toPlainText()

        config.params["zijiehuoshan_key"] = key
        config.params["zijiehuoshan_model"] = model
        config.params["zijiehuoshan_template"] = template
        Path(config.rootdir + f"/videotrans/zijie.txt").write_text(template,encoding='utf-8')
        config.getset_params(config.params)
        config.zijiew.close()

    def setallmodels():
        t = config.zijiew.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        t_list = [x for x in t.split(',') if x.strip()]
        current_text = config.zijiew.zijiehuoshan_model.currentText()
        config.zijiew.zijiehuoshan_model.clear()
        config.zijiew.zijiehuoshan_model.addItems(t_list)
        if current_text:
            config.zijiew.zijiehuoshan_model.setCurrentText(current_text)
        config.settings['zijiehuoshan_model'] = t
        json.dump(config.settings, builtin_open(config.rootdir + '/videotrans/cfg.json', 'w', encoding='utf-8'),ensure_ascii=False)

    from videotrans.component import ZijiehuoshanForm
    if config.zijiew is not None:
        config.zijiew.show()
        config.zijiew.raise_()
        config.zijiew.activateWindow()
        return
    config.zijiew = ZijiehuoshanForm()
    allmodels_str = config.settings['zijiehuoshan_model']
    allmodels = config.settings['zijiehuoshan_model'].split(',')
    config.zijiew.zijiehuoshan_model.clear()
    config.zijiew.zijiehuoshan_model.addItems(allmodels)
    config.zijiew.edit_allmodels.setPlainText(allmodels_str)
    if config.params["zijiehuoshan_key"]:
        config.zijiew.zijiehuoshan_key.setText(config.params["zijiehuoshan_key"])
    if config.params["zijiehuoshan_model"] and config.params['zijiehuoshan_model'] in allmodels:
        config.zijiew.zijiehuoshan_model.setCurrentText(config.params["zijiehuoshan_model"])

    if config.params["zijiehuoshan_template"]:
        config.zijiew.zijiehuoshan_template.setPlainText(config.params["zijiehuoshan_template"])
    config.zijiew.edit_allmodels.textChanged.connect(setallmodels)
    config.zijiew.set_zijiehuoshan.clicked.connect(save_zijiehuoshan)
    config.zijiew.test_zijiehuoshan.clicked.connect(test)
    config.zijiew.show()
