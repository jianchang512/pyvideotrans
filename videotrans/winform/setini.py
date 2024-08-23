import json

from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox, QLineEdit, QPushButton

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open

# 高级设置
def open():
    def save():
        # 创建一个空字典来存储结果
        line_edit_dict = {}

        # 使用findChildren方法查找所有QLineEdit控件
        line_edits = config.setiniw.findChildren(QLineEdit)
        # 遍历找到的所有QLineEdit控件
        for line_edit in line_edits:
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.text()
        try:
            json.dump(line_edit_dict, builtin_open(config.rootdir + "/videotrans/cfg.json", 'w', encoding='utf-8'),
                      ensure_ascii=False)
        except Exception as e:
            return QtWidgets.QMessageBox.critical(config.setiniw, config.transobj['anerror'], str(e))
        else:
            config.settings = line_edit_dict

        config.setiniw.close()

    def alert(btn):
        name = btn.objectName()[4:]
        QMessageBox.information(config.setiniw, f'Help {name}', config.setiniw.alertnotice[name])

    from videotrans.component import SetINIForm
    if config.setiniw is not None:
        config.setiniw.show()
        config.setiniw.raise_()
        config.setiniw.activateWindow()
        return
    config.setiniw = SetINIForm()
    for button in config.setiniw.findChildren(QPushButton):
        if button.objectName().startswith('btn_'):
            # 绑定clicked事件，lambda表达式传递按钮本身
            button.clicked.connect(lambda checked, btn=button: alert(btn))

    config.setiniw.set_ok.clicked.connect(save)
    config.setiniw.show()
