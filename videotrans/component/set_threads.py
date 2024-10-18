from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)
from videotrans.configure import config

class SetThreadTransDubb(QDialog):
    def __init__(self, parent=None,name='trans_thread',nums=5):
        super().__init__(parent)
        self.nums=nums
        # 设置该窗口最小宽高为 400x300
        self.resize(300, 150)

        if name == 'trans_thread':
            # 设置对话框标题
            self.setWindowTitle("设置同时翻译的字幕条数" if config.defaulelang=='zh' else "Set Translation subtitles rows")
        else:
            self.setWindowTitle('设置同时配音的并发线程数' if config.defaulelang=='zh' else "Set dubbing threads")

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        # 创建标签和输入框
        self.label = QLabel("数值:" if config.defaulelang=='zh' else "Number:")
        self.input = QLineEdit()
        self.input.setText(str(self.nums))


        # 创建按钮
        self.ok_button = QPushButton("保存" if config.defaulelang=='zh' else "Save")
        self.ok_button.clicked.connect(self.accept)  # 点击OK按钮后关闭对话框
        # 设置确认按钮高度为35
        self.ok_button.setFixedHeight(35)

        # 布局
        layout = QVBoxLayout()

        # CJK字符数布局
        num_layout = QHBoxLayout()
        num_layout.addWidget(self.label)
        num_layout.addWidget(self.input)
        layout.addLayout(num_layout)

        # OK按钮布局
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_values(self):
        num= self.input.text().strip()
        try:
            num=max(int(num),1)
        except:
            num=5
        return num
