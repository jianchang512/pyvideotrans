from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)
from videotrans.configure import config

class SubtitleSettingsDialog(QDialog):
    def __init__(self, parent=None,cjk_len=24,other_len=66):
        super().__init__(parent)
        self.cjk_len=cjk_len
        self.other_len=other_len
        self.resize(300, 200)


        # 设置对话框标题
        self.setWindowTitle("设置硬字幕行字符数" if config.defaulelang=='zh' else "Set Subtitle Length")
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        # 创建标签和输入框
        self.cjk_label = QLabel("中日韩硬字幕一行字符数:" if config.defaulelang=='zh' else "CJK Subtitle Length:")
        self.cjk_input = QLineEdit()
        self.cjk_input.setText(str(self.cjk_len))

        self.other_label = QLabel("其他语言硬字幕一行字符数:" if config.defaulelang=='zh' else "Other Language Subtitle Length:")
        self.other_input = QLineEdit()
        self.other_input.setText(str(self.other_len))

        # 创建按钮
        self.ok_button = QPushButton("保存" if config.defaulelang=='zh' else "Save")
        self.ok_button.clicked.connect(self.accept)  # 点击OK按钮后关闭对话框
        self.ok_button.setFixedHeight(35)

        # 布局
        layout = QVBoxLayout()

        # CJK字符数布局
        cjk_layout = QHBoxLayout()
        cjk_layout.addWidget(self.cjk_label)
        cjk_layout.addWidget(self.cjk_input)
        layout.addLayout(cjk_layout)

        # 其他语言字符数布局
        other_layout = QHBoxLayout()
        other_layout.addWidget(self.other_label)
        other_layout.addWidget(self.other_input)
        layout.addLayout(other_layout)

        # OK按钮布局
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_values(self):
        cjk_len,other_len= self.cjk_input.text().strip(), self.other_input.text().strip()
        try:
            cjk_len=int(cjk_len) if cjk_len else 24
            other_len=int(other_len) if other_len else 66
        except:
            cjk_len=24
            other_len=66
        return cjk_len,other_len
