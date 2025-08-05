"""

pyVideoTrans: Translate the video from one language to another and add dubbing

... (你的文件头注释保持不变) ...

"""

# ... (从 import multiprocessing 到 sys.excepthook 的所有代码保持不变) ...
# ... (这些代码在主逻辑之前运行，也会被 cProfile 捕获到，这很好) ...

import multiprocessing
import sys, os
import time
import argparse
import traceback

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["OMP_NUM_THREADS"] = str(os.cpu_count())

# ... (is_console_app 和日志重定向代码保持不变) ...

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QSize
from PySide6.QtGui import QPixmap, QIcon, QGuiApplication
from videotrans import VERSION

# 全局异常处理函数
def global_exception_hook(exctype, value, tb):
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    print(f"!!! UNHANDLED EXCEPTION !!!\n{tb_str}")

    if QtWidgets.QApplication.instance():
        error_box = QtWidgets.QMessageBox()
        error_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Application Error")
        error_box.setText("An unexpected error occurred. The application will now close.")
        error_box.setDetailedText(tb_str)
        error_box.exec()

    sys.exit(1)

sys.excepthook = global_exception_hook


parser = argparse.ArgumentParser()
parser.add_argument('--lang', type=str, help='Set the application language (e.g., en, zh)')
cli_args, unknown = parser.parse_known_args()

if cli_args.lang:
    os.environ['PYVIDEOTRANS_LANG'] = cli_args.lang.lower()


# ==================== 核心修改部分 ====================
from PySide6.QtCore import QEventLoop # 导入 QEventLoop

# 步骤1：将所有启动逻辑（除了 app.exec()）封装到一个函数中
def setup_and_show_main_window(app):
    """这个函数包含了从启动画面到主窗口显示的所有逻辑"""
    local_event_loop = QEventLoop()
    class StartWindow(QtWidgets.QWidget):
        tasks_finished = Signal()
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
            self.label.setGeometry(self.rect())

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
            
            
            self.tasks_finished.connect(local_event_loop.quit)
            self.show()
            self.center()
            # 延迟执行耗时操作，让启动窗口先显示出来
            QTimer.singleShot(0, self.run_main_tasks)

        def run_main_tasks(self):
            # 耗时的导入和初始化在这里进行
            import videotrans.ui.dark.darkstyle_rc
            with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
                # 使用 qApp 是获取 QApplication 实例的安全方式
                QtWidgets.QApplication.instance().setStyleSheet(f.read())

            from videotrans.configure import config
            from videotrans.mainwin._main_win import MainWindow

            sets = QSettings("pyvideotrans", "settings")
            w, h = int(self.width * 0.85), int(self.height * 0.85)
            size = sets.value("windowSize", QSize(w, h))
            try:
                w = size.width()
                h = size.height()
            except:
                pass
            
            # 创建主窗口
            config.MAINWIN = MainWindow(width=w, height=h)
            config.MAINWIN.move(QPoint(int((self.width - w) / 2), int((self.height - h) / 2)))
            config.MAINWIN.show() # 显示主窗口

            # 关闭启动窗口
            self.close()
            self.tasks_finished.emit()

        def center(self):
            screen = QGuiApplication.primaryScreen()
            if screen:
                screen_resolution = screen.geometry()
                self.width, self.height = screen_resolution.width(), screen_resolution.height()
                self.move(QPoint(int((self.width - 560) / 2), int((self.height - 350) / 2)))

    try:
        startwin = StartWindow()
        local_event_loop.exec()
    except Exception as e:
        msg = traceback.format_exc()
        QtWidgets.QMessageBox.critical(None, "Error", msg)

# 步骤2：创建一个 main 函数，它只负责最外层的框架
def main():
    multiprocessing.freeze_support()
    try:
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except:
        pass

    app = QtWidgets.QApplication(sys.argv)

    # -----------------------------------------------------------
    # 使用 cProfile 来运行真正的启动逻辑
    profiler = cProfile.Profile()
    # profiler 只包裹 setup_and_show_main_window，这是要分析的部分
    profiler.runcall(setup_and_show_main_window, app)
    
    # 启动逻辑运行完毕后，保存分析文件
    output_file = 'profile_output.prof'
    profiler.dump_stats(output_file)
    print(f"✅ 性能分析数据已保存到 {output_file}")
    print(f"👉 现在可以在终端运行 'snakeviz {output_file}' 来查看结果。")
    # -----------------------------------------------------------

    # 所有分析完成后，再启动事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    import cProfile
    from PySide6.QtCore import Signal # 别忘了导入 Signal

    # 直接调用 main 函数
    main()