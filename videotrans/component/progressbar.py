import re
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QProgressBar, QHBoxLayout

from videotrans.configure.config import tr
from videotrans.util import tools


class ClickableProgressBar(QLabel):
    def __init__(self, parent=None):
        super().__init__()
        self.target_dir = None
        self.msg =  tr('running')#保存最后一条日志信息，当只有进度没有消息时显示
        self.parent = parent
        self.basename = ""
        self.name = ""
        self.precent = 0
        self.duration=0#已消耗的时间秒
        self.paused = False
        self.ended = False
        self.error = ''

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

    # 正常成功结束时，如果已有出错，则不处理
    def setEnd(self):
        if self.error:
            return
        self.ended = True
        self.precent = 100
        self.progress_bar.setValue(100)
        self.setCursor(Qt.PointingHandCursor)
        self.progress_bar.setFormat(f' {self.basename}  {tr("endandopen")}')
        self.error = ''

    # 暂停，仅针对未完成的
    def setPause(self):
        if not self.ended:
            self.paused = True
            self.progress_bar.setFormat(f'  {tr("haspaused")} [{self.precent}%] {self.basename}')

    # 进度，如果进度已大于100则结束，如果小于，则取消暂停
    def setPrecent(self, p):
        self.paused = False
        if p >= 100:
            self.precent = 100
            self.error = ''
            self.setEnd()
        else:
            self.precent = p if p > self.precent else self.precent
            self.progress_bar.setValue(self.precent)
            self.progress_bar.setFormat(f' [{self.precent}%  {self.duration}]  {self.msg} {self.basename}')

    # 出错时，设置状态，停止 完成
    def setError(self, text=""):
        self.error = text
        self.ended = True
        self.progress_bar.setToolTip(
            tr("Click to view the detailed error report"))
        self.progress_bar.setFormat(f'  [{self.precent}%]  {text[:90]}   {self.basename}')

    # 设置按钮显示文字，如果已结束，则不设置，直接返回
    # 进度 set_precent 后将仅传进来时间，此时使用上次保留的msg消息
    def setText(self, text=''):
        if self.progress_bar:
            if self.ended or self.paused:
                return
            if re.match(r'^\d+?$',text):
                # 更新时间
                self.duration=text
                if self.precent < 60 and  int(text)%5==0:
                    self.precent+=0.001
            else:
                self.msg=text[:150].replace("\n",' ')
            self.progress_bar.setFormat(f' [{self.precent:.2f}%  {self.duration}s]  {self.msg} {self.basename}')  # set text format


    def mousePressEvent(self, event):
        if self.target_dir and event.button() == Qt.LeftButton:
            if self.error:
                tools.show_error(self.error)
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.target_dir))
