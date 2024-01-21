# -*- coding: utf-8 -*-
import sys
import os
import threading
from PyQt5.QtCore import Qt, QTimer
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
        os.makedirs(os.path.join(os.getcwd(), 'models'), exist_ok=True)
        os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)
        QTimer.singleShot(1000, self.run)

    def run(self):
        # 创建并显示窗口B
        try:
            from videotrans.util.tools import get_edge_rolelist
            from videotrans.mainwin.spwin import MainWindow
            threading.Thread(target=get_edge_rolelist).start()
            main = MainWindow()
            import qdarkstyle
            # with open(os.path.join(os.getcwd(), 'videotrans/styles/style.qss'), 'r', encoding='utf-8') as f:
            main.setStyleSheet("""QToolBar QToolButton {
                  background-color: #32414B;
                  height:35px;
                  margin-bottom:0px;
                  margin-top:8px;
                  margin-left:2px;
                  margin-right:0px;
                  text-align: left;
                }
                QToolBar QToolButton:hover {
                  border: 1px solid #148CD2;
                }
                QToolBar QToolButton:checked {
                  background-color: #19232D;
                  border: 1px solid #148CD2;
                }
                QToolBar QToolButton:checked:hover {
                border: 1px solid #339933;
                }
                QLabel{
                    color: #bbbbbb;
                }
                QLabel#show_tips{
                    color:#bbbbbb
                }
                QLineEdit:hover,QComboBox:hover{
                    border-color: #148cd2;
                }
                QLineEdit[readOnly="true"],QLineEdit[readOnly="true"]:hover {
                    background-color: transparent;  /* 灰色背景 */
                    border-color: transparent;  /* 灰色背景 */
                }
                QLineEdit,QComboBox{
                    background-color: #161E26;
                    border-color: #32414B;
                }
                QLineEdit:disabled {
                    background-color: transparent;  /* 灰色背景 */
                    border-color: transparent;  /* 灰色背景 */
                }
                QComboBox:disabled{
                    background-color: transparent;  /* 灰色背景 */
                    border-color: #273442;  /* 灰色背景 */
                }
                QScrollArea QPushButton{
                    background-color: rgba(50, 65, 75, 0.5);
                    border-radius: 0;
                    opacity: 0.1;
                    text-align:left;
                    padding-left:5px;
                }
                QScrollArea QPushButton:hover{
                    background-color: #19232D;
                }
            """)
            app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
            main.show()
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
