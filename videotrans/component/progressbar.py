from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QProgressBar, QHBoxLayout, QMessageBox

from videotrans.configure import config


class ClickableProgressBar(QLabel):
    def __init__(self, parent=None):
        super().__init__()
        self.target_dir = None
        self.msg = None
        self.parent = parent

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(35)
        self.progress_bar.setRange(0, 100)  # 设置进度范围
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: transparent;
                border:1px solid #32414B;
                color:#fff;
                height:35px;
                text-align:left;
                border-radius:3px;                
            }
            QProgressBar::chunk {
                width: 8px;
                border-radius:0;           
            }
        """)
        layout = QHBoxLayout(self)
        layout.addWidget(self.progress_bar)  # 将进度条添加到布局

    def setTarget(self, url):
        self.target_dir = url

    def setMsg(self, text):
        if text and config.defaulelang == 'zh':
            text += '\n\n请尝试在文档站 pyvideotrans.com 搜索错误解决方案\n'
        self.msg = text

    def setText(self, text):
        if self.progress_bar:
            self.progress_bar.setFormat(f' {text}')  # set text format

    def mousePressEvent(self, event):
        if self.target_dir and event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.target_dir))
        elif not self.target_dir and self.msg:
            QMessageBox.critical(self, config.transobj['anerror'], self.msg)
