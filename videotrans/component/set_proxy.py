from PySide6 import QtWidgets
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
)

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.util import tools


class SetThreadProxy(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.resize(400, 250)

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        # 布局
        layout = QVBoxLayout()
        # layout 顶部对齐
        layout.setAlignment(Qt.AlignTop)

        # 创建标签和输入框
        self.label = QLabel(tr("Setting up a network proxy"))
        self.input = QLineEdit()
        self.input.setText(str(config.proxy or ''))

        num_layout = QHBoxLayout()
        num_layout.addWidget(self.label)
        num_layout.addWidget(self.input)
        layout.addLayout(num_layout)

        self.setWindowTitle(tr("Setting up a network proxy"))



        # 创建按钮
        self.ok_button = QPushButton(tr("Save"))
        self.ok_button.clicked.connect(self.check_proxy)  # 点击OK按钮后关闭对话框
        # 设置确认按钮高度为35
        self.ok_button.setFixedHeight(35)


        layout.addWidget(self.ok_button)

        help_btn = QtWidgets.QPushButton()
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0);color:#777777")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Help document"))
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/proxy'))
        layout.addWidget(help_btn)

        self.setLayout(layout)

    def check_proxy(self):
        proxy = self.input.text().strip()
        if proxy:
            import re
            if not re.match(r'^(http|sock)', proxy, re.I):
                proxy = f'http://{proxy}'
            if not re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I):
                question = tools.show_popup(
                    tr("Please make sure the proxy address is correct"), tr('The network proxy address you fill in seems to be incorrect, the general proxy/vpn format is http://127.0.0.1:port, if you do not know what is the proxy please do not fill in arbitrarily, ChatGPT and other api address please fill in the menu - settings - corresponding configuration. If you confirm that the proxy address is correct, please click Yes to continue.'))
                if question != QtWidgets.QMessageBox.Yes:
                    return False
        config.settings['proxy']=proxy
        config.parse_init(config.settings)
        self.accept()

    def get_values(self):
        proxy = self.input.text().strip()
        print(f'{proxy=}')
        return proxy
