"""

pyVideoTrans: Translate the video from one language to another and add dubbing

Home-page: https://github.com/jianchang512/pyvideotrans
Author: jianchang512@gmail.com
Documents: https://pyvideotrans.com
License: GPL-V3

# 代码是一坨屎，但又不是不能跑O(∩_∩)O~别在意那些细节
# 写的这么烂，一看就不是AI写的

"""


import os,sys
import time
print(f"\n####开始启动时间:{time.time()}")




from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, QSize
from PySide6.QtGui import QPixmap, QIcon, QGuiApplication
from videotrans.configure._guiexcept import global_exception_hook, exception_handler

VERSION = "v3.78"

def show_global_error_dialog(tb_str):
    """槽函数 显示对话框。"""
    from videotrans.util.tools import show_error
    show_error(tb_str)


class StartWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.main_window = None

        self.resize(560, 350)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # 窗口背景透明

        self.background_label = QLabel(self)
        self.pixmap = QPixmap("./videotrans/styles/logo.png")
        self.background_label.setPixmap(self.pixmap)
        self.background_label.setScaledContents(True)
        self.background_label.setGeometry(self.rect())

        # 背景上叠加文字
        v_layout = QVBoxLayout(self)
        v_layout.addStretch(1)
        h_layout = QHBoxLayout()
        v_layout.addLayout(h_layout)
        h_layout.addStretch(1)
        self.status_label = QLabel(f"pyVideoTrans {VERSION} Loading...")
        self.status_label.setStyleSheet("font-size:16px; color:white; background-color:transparent;")
        h_layout.addWidget(self.status_label)
        h_layout.addStretch(1)
        v_layout.setContentsMargins(0, 0, 0, 20)

    def center(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            center_point = screen.geometry().center()
            self.move(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2)

def initialize_full_app(start_window, app_instance):    
    import os
    import argparse
    import traceback
      

    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    os.environ["OMP_NUM_THREADS"] = str(os.cpu_count())

    # 日志
    if sys.stdout is None or sys.stderr is None:
        try:
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"app-log-{time.strftime('%Y-%m-%d')}.txt")
            log_file = open(log_file_path, 'a', encoding='utf-8', buffering=1)
            sys.stdout = log_file
            sys.stderr = log_file
            print(f"\n\n--- Application started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        except Exception:
            pass


    sys.excepthook = global_exception_hook

    # 命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', type=str, help='Set the application language (e.g., en, zh)')
    cli_args, unknown = parser.parse_known_args()
    if cli_args.lang:
        os.environ['PYVIDEOTRANS_LANG'] = cli_args.lang.lower()

    # 导入qss image 资源
    import videotrans.ui.dark.darkstyle_rc 
    with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
        app_instance.setStyleSheet(f.read())
    
    from videotrans.configure import config 
    from videotrans.mainwin._main_win import MainWindow
    
    main_window_created = False
    try:
        from PySide6.QtCore import QSettings
        screen = QGuiApplication.primaryScreen().geometry()
        sets = QSettings("pyvideotrans", "settings")
        w, h = int(screen.width() * 0.85), int(screen.height() * 0.85)
        size = sets.value("windowSize", QSize(w, h))
        w, h = size.width(), size.height()        
        start_window.main_window = MainWindow(width=w, height=h)
        exception_handler.show_exception_signal.connect(show_global_error_dialog)
        main_window_created=True
    except Exception as e:
        sys.excepthook(type(e), e, e.__traceback__)
        app_instance.quit()
        return

    # 显示主窗口
    if main_window_created and start_window.main_window:
        print(f"#### 所有初始化完毕，准备关闭启动窗口: {time.time()}")
        start_window.main_window.show()
        QTimer.singleShot(1000, lambda: start_window.close())

if __name__ == "__main__":
    # Windows 打包需要
    import multiprocessing
    multiprocessing.freeze_support()
    
    # 设置 HighDpi
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass
    

    app = QApplication(sys.argv)
    
    splash = StartWindow()
    splash.setWindowIcon(QIcon("./videotrans/styles/icon.ico"))
    splash.center()
    splash.show()
    
    QTimer.singleShot(50, lambda: initialize_full_app(splash, app))
    sys.exit(app.exec())