"""
pyVideoTrans: Translate the video from one language to another and add dubbing

Home-page: https://github.com/jianchang512/pyvideotrans
Author: jianchang512@gmail.com
Documents: https://pyvideotrans.com
Discuss: https://bbs.pyvideotrans.com
License: GPL-V3 <https://www.gnu.org/licenses/gpl-3.0.html>

码不在雅，能跑则灵。
型不在秀，兼容就行。
全是烂码，Bug多多。
全局变量乱如麻，if分支叠成塔。
线程队列八九个，传参全靠大字典。
可以塞硬件，怼系统。
无单元之测试，无类型之规整。
启动加载三百秒，界面UI丑到爆。
前有Whisper卡进程，后有FF猛报错。
三大平台皆可跑，上万星友亦成行。
AI嘲: 码之烂平生仅见
作者云：又不是不能跑。

"""

import os
import atexit, sys, time
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt, qInstallMessageHandler, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication, QIcon
import argparse
import tempfile
from pathlib import Path
from PySide6.QtCore import QSize, QSettings
import traceback
from videotrans import VERSION
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 抑制警告
def suppress_qt_warnings(msg_type, context, message):
    if "QThreadStorage" in message:
        return


def cleanup():
    """强制清理函数"""
    try:
        if 'app' in globals():
            app.quit()
    except:
        pass


def show_global_error_dialog(exctype, value, tb):
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    QMessageBox.critical(None, 'Error', tb_str)


# 启动画面
class StartWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.main_window = None
        self.LoadNotif = None
        self.start_time = time.time()
        self.loader = None
        self.setWindowTitle('pyVideoTrans')
        self.screen=None

        self.resize(560, 350)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 窗口背景透明

        self.background_label = QLabel(self)
        self.pixmap = QPixmap("./videotrans/styles/logo.png")
        self.background_label.setPixmap(self.pixmap)
        self.background_label.setScaledContents(True)
        self.background_label.setGeometry(self.rect())

        # 背景上叠加文字
        v_layout = QVBoxLayout(self)
        v_layout.addStretch(1)
        self.status_label = QLabel(f"pyVideoTrans {VERSION} Loading...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setStyleSheet("font-size:16px; color:white; background-color:transparent;")

        v_layout.addWidget(self.status_label)
        v_layout.setContentsMargins(0, 0, 0, 20)

    def closeEvent(self, event):
        # 释放启动画面的资源
        if hasattr(self, 'pixmap') and self.pixmap:
            self.pixmap = None

        # 如果主窗口不存在，则退出应用程序
        if self.main_window is None:
            QApplication.instance().quit()

        super().closeEvent(event)

    def update_lable(self, t):
        print(f'{int(time.time())}:{t}')
        if t == 'end':
            self.status_label.setText(f'Total time {int(time.time() - self.start_time)}s')
            QTimer.singleShot(1000, lambda: self.close())
        else:
            self.status_label.setText(f'{t}  {int(time.time() - self.start_time)}s')
        QApplication.processEvents()

    def center(self):
        self.screen = QGuiApplication.primaryScreen().geometry()
        if self.screen:
            center_point = self.screen.center()
            self.move(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2)


# 启动主窗口
def initialize_full_app(start_window, app_instance):
    if sys.stdout is None or sys.stderr is None:
        try:
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"{time.strftime('%Y%m%d')}.log")
            log_file = open(log_file_path, 'a', encoding='utf-8', buffering=1)
            sys.stdout = log_file
            sys.stderr = log_file
            print(f"\n\n--- Application started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        except Exception as e:
            print(e)

    sys.excepthook = show_global_error_dialog

    # 命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', type=str, help='Set the application language (e.g., en, zh)')
    cli_args, unknown = parser.parse_known_args()
    if cli_args.lang:
        os.environ['PYVIDEOTRANS_LANG'] = cli_args.lang.lower()
    start_window.update_lable('Loading resources...')
    # 导入qss image 资源
    import videotrans.ui.dark.darkstyle_rc
    with open('./videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
        app_instance.setStyleSheet(f.read())
    start_window.update_lable('Loading main window...')

    from videotrans.mainwin.main_win import MainWindow
    try:
        screen = start_window.screen
        w, h = int(screen.width()), int(screen.height())
        sets = QSettings("pyvideotrans", "settings")
        size = sets.value("windowSize", QSize(min(int(w*0.9),1400), min(int(h*0.85),800)))
        start_window.update_lable('Initializing UI...')
        start_window.main_window = MainWindow(width=size.width(), height=size.height(),callback=start_window.update_lable,screen_size=[w,h])
        center_point = screen.center()
        start_window.main_window.move(center_point.x() - size.width() // 2, center_point.y() - size.height() // 2)
    except Exception as e:
        show_global_error_dialog(type(e), e, e.__traceback__)
        app_instance.quit()
        return

def fix_stdio():
    if sys.stdout is None or sys.stderr is None:
        try:
            import ctypes
            if ctypes.windll.kernel32.AttachConsole(-1):
                if sys.stdout is None:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                if sys.stderr is None:
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                return
        except Exception:
            pass

        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")

def check_and_run_external_script():
    """
    检查是否作为脚本解释器启动。
    例如运行：sp.exe xxx.py arg1 arg2
    import subprocess
    subprocess.run([sys.executable, r"test.py"])
    import subprocess
    subprocess.run([sys.executable, r"test.py","a","b"])
    """
    if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
        fix_stdio()  
        import runpy
        script_path = os.path.abspath(sys.argv[1])
        if script_path and os.path.isfile(script_path):
            # 将 script_path 的所在目录加入 sys.path，保证脚本内导入本地模块正常
            script_dir = os.path.dirname(script_path)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)

            # 重构 sys.argv，让外部脚本读取到的 sys.argv 是正常的（sys.argv[0] 是脚本自身）
            sys.argv = sys.argv[1:]

            # 执行外部脚本
            runpy.run_path(script_path, run_name='__main__')
            sys.exit(0)


if __name__ == "__main__":
    check_and_run_external_script()

    # Windows 打包需要
    import multiprocessing

    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)
    qInstallMessageHandler(suppress_qt_warnings)
    atexit.register(cleanup)
    if sys.platform != "win32":
        import signal


        def handle_exit(signum, frame):
            cleanup()
            sys.exit(0)


        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

    # 设置 HighDpi
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass

    app = QApplication(sys.argv)
    res = 0
    if getattr(sys, 'frozen', False) and (Path(sys.executable).parent.as_posix()).startswith(
            Path(tempfile.gettempdir()).as_posix()):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle('Error')
        msg_box.setText('请解压后再双击 sp.exe，不可直接压缩包内使用')
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        msg_box.exec()
        app.quit()
    else:
        splash = StartWindow()
        splash.setWindowIcon(QIcon("./videotrans/styles/icon.ico"))
        splash.center()
        splash.show()

        QTimer.singleShot(100, lambda: initialize_full_app(splash, app))
        try:
            res = app.exec()
            res = 0 if res is None else res
        finally:
            try:
                cleanup()
                #import gc
                #gc.collect()
            except Exception as e:
                print(e)
    sys.exit(res if isinstance(res, int) else 0)
