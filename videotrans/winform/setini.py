# 高级设置
from videotrans.task.simple_runnable_qt import run_in_threadpool


def openwin():

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox, QLineEdit, QPlainTextEdit, QPushButton, QCheckBox, QComboBox

    from videotrans.configure import config
    from videotrans.util import tools
    from pathlib import Path
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
                if name=='hf_token':
                    Path(config.ROOT_DIR + "/models/hf_token.txt").write_text(line_edit.text().strip())
        for line_edit in winobj.findChildren(QPlainTextEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                if name in ['model_list','Whisper.cpp.models'] and line_edit.toPlainText() != line_edit_dict[name]:
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
                if name=='video_codec':
                    line_edit_dict[name]=int(line_edit.currentText())
                else:
                    # 将objectName作为key，text作为value添加到字典中
                    line_edit_dict[name] = line_edit.currentText()

        line_edit_dict['homedir'] = winobj.homedir_btn.text()
        
        config.settings = config.parse_init(line_edit_dict)
        
        if shoud_model_list_sign:
            tools.set_process(text="", type='refreshmodel_list')

        winobj.close()


    def create():
        nonlocal winobj
        from videotrans.component.set_form import SetINIForm
        winobj=config.child_forms.get('setini')
        if winobj:
            winobj.show()
            return
        winobj = SetINIForm()
        config.child_forms['setini'] = winobj
        winobj.set_ok.clicked.connect(save)
        
        winobj.show()

    QTimer.singleShot(100, create)
