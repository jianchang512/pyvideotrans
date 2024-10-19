from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)
from videotrans.configure import config

class SetThreadTransDubb(QDialog):
    def __init__(self, parent=None,name='trans',nums=5,sec=0):
        super().__init__(parent)
        self.nums=nums
        self.sec=sec
        # 设置该窗口最小宽高为 400x300
        self.resize(300, 200)

        if name == 'trans':
            # 设置对话框标题
            self.setWindowTitle("设置同时翻译的字幕条数和暂停秒" if config.defaulelang=='zh' else "Set Translation subtitles rows")
            wait_msg='暂停秒:' if config.defaulelang=='zh' else "Wait/s:"
        else:
            wait_msg='暂停秒/并发为1时生效:' if config.defaulelang=='zh' else "Wait/s/1 thread:"
            self.setWindowTitle('设置同时配音的并发线程数和暂停秒' if config.defaulelang=='zh' else "Set dubbing threads")

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        # 创建标签和输入框
        self.label = QLabel("并发数:" if config.defaulelang=='zh' else "Number:")
        self.input = QLineEdit()
        self.input.setText(str(self.nums))


        self.wait_label = QLabel(wait_msg)
        self.wait_input = QLineEdit()
        self.wait_input.setText(str(self.sec))


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

        wait_layout = QHBoxLayout()
        wait_layout.addWidget(self.wait_label)
        wait_layout.addWidget(self.wait_input)
        layout.addLayout(wait_layout)

        # OK按钮布局
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_values(self):
        num,wait= self.input.text().strip(),self.wait_input.text().strip()
        try:
            num,wait=max(int(num),1),max(round(float(wait),1),0)
        except:
            num=5
            wait=0
        return num,wait
