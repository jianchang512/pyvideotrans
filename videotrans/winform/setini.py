# 高级设置

def openwin():

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox, QLineEdit, QPlainTextEdit, QPushButton, QCheckBox, QComboBox

    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from pathlib import Path
    winobj = None

    def save():
        # 创建一个空字典来存储结果
        shoud_model_list_sign = False
        # 遍历找到的所有QLineEdit控件
        for line_edit in winobj.findChildren(QLineEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                settings[name] = line_edit.text()
                if name=='hf_token':
                    Path(ROOT_DIR + "/models/hf_token.txt").write_text(line_edit.text().strip())
        for line_edit in winobj.findChildren(QPlainTextEdit):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                if name in ['model_list','Whisper_cpp_models'] and line_edit.toPlainText() != settings[name]:
                    shoud_model_list_sign = True
                # 将objectName作为key，text作为value添加到字典中
                settings[name] = line_edit.toPlainText()
        for line_edit in winobj.findChildren(QCheckBox):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                # 将objectName作为key，text作为value添加到字典中
                settings[name] = line_edit.isChecked()
        for line_edit in winobj.findChildren(QComboBox):
            # 检查QLineEdit是否有objectName
            if hasattr(line_edit, 'objectName') and line_edit.objectName():
                name = line_edit.objectName()
                if name=='video_codec':
                    settings[name]=int(line_edit.currentText())
                else:
                    # 将objectName作为key，text作为value添加到字典中
                    settings[name] = line_edit.currentText()

        settings['homedir'] = winobj.homedir_btn.text()
        
        settings.save()
        
        if shoud_model_list_sign:
            tools.set_process(text="", type='refreshmodel_list')

        winobj.close()


    def create():
        nonlocal winobj
        from videotrans.component.set_form import SetINIForm
        winobj=app_cfg.child_forms.get('setini')
        if winobj:
            winobj.show()
            return
        winobj = SetINIForm()
        app_cfg.child_forms['setini'] = winobj
        winobj.set_ok.clicked.connect(save)
        
        winobj.show()

    QTimer.singleShot(100, create)
