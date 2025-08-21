# 高级设置
def openwin():
    import json

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox, QLineEdit, QPlainTextEdit, QPushButton, QCheckBox, QComboBox

    from videotrans.configure import config
    from videotrans.util import tools
    winobj = None

    def save():
        # 创建一个空字典来存储结果
        line_edit_dict = config.settings
        shoud_model_list_sign = False

        # 遍历找到的所有QLineEdit控件
        for line_edit in winobj.findChildren(QLineEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.text()
        for line_edit in winobj.findChildren(QPlainTextEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                if name == 'model_list' and line_edit.toPlainText() != line_edit_dict[name]:
                    shoud_model_list_sign = True
                # 将objectName作为key，text作为value添加到字典中
                line_edit_dict[name] = line_edit.toPlainText()
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
                if name == 'subtitle_position':
                    # 根据位置字符串，选择对应的数字
                    line_edit_dict[name] = config.POSTION_ASS_VK.get(line_edit.currentText(), 2)
                elif name == 'borderStyle':
                    # 背景风格 0位置代表轮廓，1位置代表背景色
                    line_edit_dict[name] = 1 if line_edit.currentIndex() == 0 else 3
                else:
                    # 将objectName作为key，text作为value添加到字典中
                    line_edit_dict[name] = line_edit.currentText()

        line_edit_dict['homedir'] = winobj.homedir_btn.text()
        try:
            config.parse_init(line_edit_dict)
        except Exception as e:
            return tools.show_error(str(e))
        else:
            config.settings = line_edit_dict
            if shoud_model_list_sign:
                tools.set_process(text="", type='refreshmodel_list')

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

    QTimer.singleShot(100, create)
