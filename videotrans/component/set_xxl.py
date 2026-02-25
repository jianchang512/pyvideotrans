from PySide6 import QtWidgets
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
from videotrans.util import tools


class SetFasterXXL(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.resize(800, 250)

        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))

        # 布局
        layout = QVBoxLayout()
        # layout 顶部对齐
        layout.setAlignment(Qt.AlignTop)

        # 创建标签和输入框
        self.label = QPushButton(tr("Click on faster-xxl"))
        self.input = QLineEdit()
        self.input.setReadOnly(True)
        self.input.setText(settings.get('Faster_Whisper_XXL',''))
        self.label.clicked.connect(self.selectxxl)
        
        num_layout = QHBoxLayout()
        num_layout.addWidget(self.label)
        num_layout.addWidget(self.input)
        layout.addLayout(num_layout)

        self.setWindowTitle(tr("Click on faster-xxl"))



        # 创建按钮
        self.ok_button = QPushButton(tr("Save"))
        self.ok_button.clicked.connect(self.accept)  # 点击OK按钮后关闭对话框
        # 设置确认按钮高度为35
        self.ok_button.setFixedHeight(35)


        layout.addWidget(self.ok_button)

        help_btn = QtWidgets.QPushButton()
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0);color:#777777")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Help document"))
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/xxl'))
        layout.addWidget(help_btn)

        self.setLayout(layout)

    def selectxxl(self):
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path
        exe, _ = QFileDialog.getOpenFileName(self, tr("Select faster-whisper-xxl.exe"), Path.home().as_posix(), f'Files(*.exe)')
        if exe:
            settings['Faster_Whisper_XXL'] = Path(exe).as_posix()
            self.input.setText(settings['Faster_Whisper_XXL'])
            settings.save()

    def get_values(self):
        return self.input.text().strip()
