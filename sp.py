# -*- coding: utf-8 -*-
import sys
import os
import threading
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtGui import QPixmap, QPalette, QBrush, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget

class StartWindow(QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        # 设置窗口无边框和标题
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口的背景图片
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap("videotrans/styles/logo.png")))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setWindowIcon(QIcon(os.path.join(os.getcwd(), "videotrans/styles/icon.ico")))
        # 窗口大小
        self.resize(800, 500)
        self.center()
        self.show()
        # 使用QTimer延时显示窗口B
        QTimer.singleShot(1000, self.run)

    def run(self):
        # 创建并显示窗口B
        try:
            from videotrans.util import tools
            from videotrans.mainwin.spwin import MainWindow
            os.makedirs(os.path.join(os.getcwd(),'models'), exist_ok=True)
            os.makedirs(os.path.join(os.getcwd(),'tmp'), exist_ok=True)
            threading.Thread(target=tools.get_edge_rolelist).start()
            threading.Thread(target=tools.get_elevenlabs_role, args=(True,)).start()
            main = MainWindow()
            import qdarkstyle
            with open(os.path.join(os.getcwd(), 'videotrans/styles/style.qss'), 'r', encoding='utf-8') as f:
                main.setStyleSheet(f.read())
            app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        except Exception as e:
            print(f'main window {str(e)}')
        self.close()

    def center(self):
        qtRect = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRect.moveCenter(centerPoint)
        self.move(qtRect.topLeft())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        startwin = StartWindow()
    except Exception as e:
        print(f"error:{str(e)}")
    sys.exit(app.exec())
