# 高级设置


def openwin():
    from videotrans.winform import get_cls
    from videotrans.util.help_misc import set_process
    from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QCheckBox, QComboBox
    from videotrans.configure.config import ROOT_DIR, app_cfg,settings
    from pathlib import Path

    def save():
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
                if name=='llm_ai_type':
                    settings[name]=line_edit.currentIndex()
                elif name=='video_codec':
                    settings[name]=int(line_edit.currentText())
                else:
                    # 将objectName作为key，text作为value添加到字典中
                    settings[name] = line_edit.currentText()

        settings['homedir'] = winobj.homedir_btn.text()
        
        settings.save()
        

        winobj.close()


    winobj = get_cls(Path(__file__).stem)()
    winobj.set_ok.clicked.connect(save)
    return winobj
