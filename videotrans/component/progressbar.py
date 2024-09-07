from pathlib import Path

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
        self.basename = ""
        self.name = ""
        self.precent = 0
        self.ended=False

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

    def setTarget(self, target_dir=None, name=None):
        self.target_dir = target_dir
        self.name = name
        self.basename = Path(name).name

    def setEnd(self):
        self.ended=True
        self.precent = 100
        self.progress_bar.setValue(100)
        self.setCursor(Qt.PointingHandCursor)
        self.progress_bar.setFormat(f' {self.basename}  {config.transobj["endandopen"]}')
    def setPrecent(self,p):
        self.precent=p
        if p>=100:
            self.setEnd()
    def setError(self,text=""):
        self.ended=True
        self.setText(text)

    def setText(self, text=''):
        if self.progress_bar:
            if self.ended:
                return
            if not text:
                text = config.transobj['running']
            self.progress_bar.setFormat(f'  [{self.precent}%]  {text}   {self.basename}')  # set text format

    def mousePressEvent(self, event):
        if self.target_dir and event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.target_dir))
        elif not self.target_dir and self.msg:
            QMessageBox.critical(self, config.transobj['anerror'], self.msg)
