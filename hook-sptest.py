"""

pyVideoTrans: Translate the video from one language to another and add dubbing

Home-page: https://github.com/jianchang512/pyvideotrans
Author: jianchang512@gmail.com
Documents: https://pyvideotrans.com
License: GPL-V3

# 代码是一坨屎，但又不是不能跑O(∩_∩)O~
# 代码越写越是坨屎，好烦

"""
try:
    import pyi_splash

    # Update the text on the splash screen
    pyi_splash.update_text("pyVideoTrans!")
    
except:
    pass
# Close the splash screen. It does not matter when the call
# to this function is made, the splash screen remains open until
# this function is called or the Python program is terminated.


import multiprocessing
import sys, os
import time

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QSize
from PySide6.QtGui import QPixmap, QIcon, QGuiApplication

from videotrans import VERSION

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

'''
class StartWindow(QtWidgets.QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        self.width = 1200
        self.height = 700
        self.resize(560, 350)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
       
        self.label = QtWidgets.QLabel(self)
        self.pixmap = QPixmap("./videotrans/styles/logo.png")
        self.label.setPixmap(self.pixmap)
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(self.rect()) #直接设置几何形状覆盖

        self.setWindowIcon(QIcon("./videotrans/styles/icon.ico"))
        
        
        
        v1 = QtWidgets.QVBoxLayout()
        v1.addStretch(1)
        h1 = QtWidgets.QHBoxLayout()
        v1.addLayout(h1)
        v1.addStretch(0)
        h1.addStretch(1)
        self.lab = QtWidgets.QLabel()
        self.lab.setStyleSheet("""font-size:16px;color:#fff;text-align:center;background-color:transparent""")
        self.lab.setText(f"pyVideoTrans {VERSION} Loading...")
        h1.addWidget(self.lab)
        h1.addStretch(0)
        self.setLayout(v1)
        
        self.show()
        self.center()
        QTimer.singleShot(100, self.run)

    def run(self):
        # 创建并显示窗口B
        print(time.time())
        import videotrans.ui.dark.darkstyle_rc
        with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        from videotrans.configure import config
        try:
            from videotrans.mainwin._main_win import MainWindow
            sets=QSettings("pyvideotrans", "settings")
            w,h=int(self.width*0.85), int(self.height*0.85)
            size = sets.value("windowSize", QSize(w,h))
            try:
                w=size.width()
                h=size.height()
            except:
                pass
            config.MAINWIN=MainWindow(width=w, height=h)
            config.MAINWIN.move(QPoint(int((self.width - w) / 2), int((self.height - h) / 2)))
        except Exception as e:
            import traceback
            from PySide6.QtWidgets import QMessageBox
            msg=traceback.format_exc()
            if msg.find('torch._C')>0:
                QtWidgets.QMessageBox.critical(startwin,"Error",'因底层torch升级，请重新下载完整包' if config.defaulelang=='zh' else 'Please download the full package again')
            else:
                QtWidgets.QMessageBox.critical(startwin,"Error",msg)
        finally:
            try:
                import pyi_splash
                pyi_splash.close()
            except:
                pass
        print(time.time())
        QTimer.singleShot(500, lambda :self.close())

    def center(self):
        screen = QGuiApplication.primaryScreen()
        screen_resolution = screen.geometry()
        self.width, self.height = screen_resolution.width(), screen_resolution.height()
        self.move(QPoint(int((self.width - 560) / 2), int((self.height - 350) / 2)))

'''
if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows 上需要这个来避免子进程的递归执行问题
    try:
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except:
        pass

    app = QtWidgets.QApplication(sys.argv)
    startwin = None
    try:
        #startwin = StartWindow()
            
        from videotrans.mainwin._main_win import MainWindow
        sets=QSettings("pyvideotrans", "settings")
        screen = QGuiApplication.primaryScreen()
        screen_resolution = screen.geometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        w,h=int(width*0.85), int(height*0.85)
        size = sets.value("windowSize", QSize(w,h))
        try:
            w=size.width()
            h=size.height()
        except:
            pass
        from videotrans.configure import config
        config.MAINWIN=MainWindow(width=w, height=h)
        config.MAINWIN.move(QPoint(int((width - w) / 2), int((height - h) / 2)))
        try:
            import pyi_splash
            pyi_splash.close()
        except:
            pass
    except Exception as e:
        import traceback
        msg=traceback.format_exc()
        QtWidgets.QMessageBox.critical(None,"Error",msg)
    sys.exit(app.exec())
