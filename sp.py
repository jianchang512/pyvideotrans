# -*- coding: utf-8 -*-
import sys
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPalette, QBrush, QIcon, QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget
from videotrans.mainwin.spwin import MainWindow



class StartWindow(QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        # 设置窗口无边框和标题
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口的背景图片
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(QPixmap("videotrans/styles/logo.png")))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setWindowIcon(QIcon(os.path.join(os.getcwd(), "videotrans/styles/icon.ico")))
        # 窗口大小
        self.resize(560, 350)
        self.center()
        self.show()
        # 使用QTimer延时显示窗口B
        os.makedirs(os.path.join(os.getcwd(), 'models'), exist_ok=True)
        os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
        QTimer.singleShot(500, self.run)


    def run(self):
        # 创建并显示窗口B
        try:
            main = MainWindow()
            import qdarkstyle
            with open(os.path.join(os.getcwd(),'videotrans/styles/style.qss'),'r',encoding="utf-8") as f:
                main.setStyleSheet(f.read())
            app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyside6"))

            main.show()
            self.close()
        except Exception as e:
            print(f'main window {str(e)}')



    def center(self):
        screen=QGuiApplication.primaryScreen()
        qtRect = self.frameGeometry()
        qtRect.moveCenter(screen.availableGeometry().center())
        reso=screen.geometry()
        self.width, self.height=reso.width(), reso.height()       
        self.move(qtRect.topLeft())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        startwin = StartWindow()
    except Exception as e:
        print(f"error:{str(e)}")
    sys.exit(app.exec())
