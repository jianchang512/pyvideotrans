import json

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox, QLineEdit, QPushButton, QCheckBox, QComboBox

from videotrans.configure import config
from videotrans.util import tools


# 高级设置
def openwin():
    winobj=None
    def save():
        # 创建一个空字典来存储结果
        line_edit_dict = config.settings
        shoud_model_list_sign=False

        # 遍历找到的所有QLineEdit控件
        for line_edit in winobj.findChildren(QLineEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                if name=='model_list' and line_edit.text() != line_edit_dict[name]:
                    shoud_model_list_sign=True
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.text()
        for line_edit in winobj.findChildren(QCheckBox):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.isChecked()
        for line_edit in winobj.findChildren(QComboBox):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.currentText()

        line_edit_dict['homedir']=winobj.homedir_btn.text()
        try:
            with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(line_edit_dict, ensure_ascii=False))
        except Exception as e:
            return QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], str(e))
        else:
            config.settings = line_edit_dict
            if shoud_model_list_sign:
                tools.set_process(text="",type='refreshmodel_list')

        winobj.close()

    def alert(btn):
        name = btn.objectName()[4:]
        QMessageBox.information(winobj, f'Help {winobj.titles[name]}', winobj.alertnotice[name])
    def create():
        nonlocal winobj
        from videotrans.component import SetINIForm
        
        
        winobj = SetINIForm()
        config.child_forms['setiniw'] = winobj
        for button in winobj.findChildren(QPushButton):
            if button.objectName().startswith('btn_'):
                button.clicked.connect(lambda checked, btn=button: alert(btn))
        winobj.set_ok.clicked.connect(save)
        winobj.show()
    QTimer.singleShot(100,create)