from PySide6 import QtWidgets
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)
from videotrans.configure import config
from videotrans.util import tools


class SetThreadTransDubb(QDialog):
    def __init__(self, parent=None,name='trans',nums=5,sec=0,ai_nums=500):
        super().__init__(parent)
        self.nums=nums
        self.sec=sec
        self.name=name
        self.ai_nums=ai_nums
        # 设置该窗口最小宽高为 400x300
        self.resize(400, 250)

        

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        
        # 布局
        layout = QVBoxLayout()
        # layout 顶部对齐
        layout.setAlignment(Qt.AlignTop)
        
        # 创建标签和输入框
        if name == 'trans':
            self.label = QLabel("传统翻译每次字幕行数:" if config.defaulelang=='zh' else "Subtitles lines:")
        else:
            self.label = QLabel("并发数:" if config.defaulelang=='zh' else "Number:")
        self.input = QLineEdit()
        self.input.setText(str(self.nums))
        
        num_layout = QHBoxLayout()
        num_layout.addWidget(self.label)
        num_layout.addWidget(self.input)
        layout.addLayout(num_layout)
        
        
        if name == 'trans':
            # 设置对话框标题
            self.setWindowTitle("设置同时翻译的字幕条数和暂停秒" if config.defaulelang=='zh' else "Set Translation subtitles rows")
            wait_msg='暂停秒:' if config.defaulelang=='zh' else "Wait/s:"
            
            self.ailabel = QLabel("AI翻译每次字幕行数:" if config.defaulelang=='zh' else "Number:")
            self.aiinput = QLineEdit()
            self.aiinput.setText(str(self.ai_nums))
            ainum_layout = QHBoxLayout()
            ainum_layout.addWidget(self.ailabel)
            ainum_layout.addWidget(self.aiinput)
            layout.addLayout(ainum_layout)
            
        else:
            wait_msg='暂停秒/并发为1时生效:' if config.defaulelang=='zh' else "Wait/s/1 thread:"
            self.setWindowTitle('设置同时配音的并发线程数和暂停秒' if config.defaulelang=='zh' else "Set dubbing threads")


        self.wait_label = QLabel(wait_msg)
        self.wait_input = QLineEdit()
        self.wait_input.setText(str(self.sec))
        tips_msg='每完成一次请求后的暂停等待秒数，用于防止某些渠道限流出错' if config.defaulelang=='zh' else 'The number of seconds to pause and wait after each completed request'
        self.wait_input.setToolTip(tips_msg)


        # 创建按钮
        self.ok_button = QPushButton("保存" if config.defaulelang=='zh' else "Save")
        self.ok_button.clicked.connect(self.accept)  # 点击OK按钮后关闭对话框
        # 设置确认按钮高度为35
        self.ok_button.setFixedHeight(35)

        


        

        wait_layout = QHBoxLayout()
        wait_layout.addWidget(self.wait_label)
        wait_layout.addWidget(self.wait_input)
        layout.addLayout(wait_layout)

        tips_label=QLabel()
        tips_label.setText(tips_msg)
        # OK按钮布局
        layout.addWidget(tips_label)
        layout.addWidget(self.ok_button)
        if name=='trans':
            help_btn = QtWidgets.QPushButton()
            help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0);color:#777777")
            help_btn.setObjectName("help_btn")
            help_btn.setCursor(Qt.PointingHandCursor)
            help_btn.setText("查看如何选择翻译渠道教程" if config.defaulelang == 'zh' else "Help document")
            help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/selecttranslate'))
            layout.addWidget(help_btn)

        self.setLayout(layout)

    def get_values(self):
        num,wait= self.input.text().strip(),self.wait_input.text().strip()
        ainum=0
        if self.name=='trans':
            ainum=int(self.aiinput.text().strip())
        try:
            num,wait=max(int(num),1),max(round(float(wait),1),0)
        except:
            num=5
            wait=0
        return num,wait,ainum
