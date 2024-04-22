# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import time

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPalette, QBrush, QIcon, QGuiApplication

VERSION = 'v1.55'


class StartWindow(QtWidgets.QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        # 设置窗口无边框和标题
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口的背景图片
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(QPixmap("./videotrans/styles/logo.png")))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setWindowIcon(QIcon(".videotrans/styles/icon.ico"))
        v1 = QtWidgets.QVBoxLayout()
        v1.addStretch(1)
        h1 = QtWidgets.QHBoxLayout()
        v1.addLayout(h1)
        v1.addStretch(0)

        h1.addStretch(1)
        self.lab = QtWidgets.QLabel()
        self.lab.setText(f"pyVideoTrans {VERSION} loading...")
        self.lab.setStyleSheet("""font-size:16px;color:#fff;text-align:center""")
        h1.addWidget(self.lab)
        h1.addStretch(0)
        self.setLayout(v1)

        # 窗口大小
        self.resize(560, 350)
        self.center()
        self.show()
        # 使用QTimer延时显示窗口B
        QTimer.singleShot(200, self.run)

    def run(self):
        global qss
        # 创建并显示窗口B
        try:
            nostyle=Path("./nostyle.txt")
            st = time.time()
            from videotrans.mainwin.spwin import MainWindow
            main = MainWindow()
            # loadtime = 0
            if not nostyle.exists():
                with open('./videotrans/styles/stylenoimg.qss', 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
            # main.show()
            file=Path(Path.cwd()/"tmp")
            file.mkdir(parents=True, exist_ok=True)
            et = time.time()
            self.close()
            print(f'启动用时：{et - st}')
            if not nostyle.exists():
                import videotrans.ui.dark.darkstyle_rc
                with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
        except Exception as e:
            print(f'main window {str(e)}')

    def center(self):
        screen = QGuiApplication.primaryScreen()
        qtRect = self.frameGeometry()
        qtRect.moveCenter(screen.availableGeometry().center())
        self.move(qtRect.topLeft())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    try:
        startwin = StartWindow()
    except Exception as e:
        print(f"error:{str(e)}")
    sys.exit(app.exec())
