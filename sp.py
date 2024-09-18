# -*- coding: utf-8 -*-
# 代码是一坨屎，但又不是不能跑O(∩_∩)O~
import multiprocessing
import sys, os
import time

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QPalette, QBrush, QIcon, QGuiApplication

from videotrans import VERSION

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

class StartWindow(QtWidgets.QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        self.width = 1200
        self.height = 700
        # 设置窗口无边框和标题
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口的背景图片
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(QPixmap("./videotrans/styles/logo.png")))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setWindowIcon(QIcon("./videotrans/styles/icon.ico"))
        v1 = QtWidgets.QVBoxLayout()
        v1.addStretch(1)
        h1 = QtWidgets.QHBoxLayout()
        v1.addLayout(h1)
        v1.addStretch(0)

        h1.addStretch(1)
        self.lab = QtWidgets.QLabel()
        self.lab.setText(f"pyVideoTrans {VERSION} Loading...")
        self.lab.setStyleSheet("""font-size:16px;color:#fff;text-align:center""")
        h1.addWidget(self.lab)
        h1.addStretch(0)
        self.setLayout(v1)

        # 窗口大小
        self.resize(560, 350)
        self.show()
        self.center()
        QTimer.singleShot(100, self.run)

    def run(self):
        # 创建并显示窗口B
        print(time.time())
        import videotrans.ui.dark.darkstyle_rc
        with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        try:
            from videotrans.mainwin._main_win import MainWindow
            MainWindow(width=self.width, height=self.height)
        except Exception as e:
            import traceback
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self,"Error",traceback.format_exc())
            
        print(time.time())
        self.close()

    def center(self):
        screen = QGuiApplication.primaryScreen()
        screen_resolution = screen.geometry()
        self.width, self.height = screen_resolution.width(), screen_resolution.height()
        self.move(QPoint(int((self.width - 560) / 2), int((self.height - 350) / 2)))


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows 上需要这个来避免子进程的递归执行问题
    app = QtWidgets.QApplication(sys.argv)
    try:
        startwin = StartWindow()
    except Exception as e:
        import traceback
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(app,"Error",traceback.format_exc())
    sys.exit(app.exec())
