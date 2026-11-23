import os
import subprocess
import sys
from pathlib import Path

class LifecycleMixin:

    def restart_app(self):
        from PySide6.QtWidgets import QMessageBox
        from videotrans.configure.config import tr

        reply = QMessageBox.question(
            self,
            tr("Restart"),
            tr("Are you sure you want to restart the application?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.is_restarting = True
            self.close()

    def closeEvent(self, event):
        self.hide()
        from videotrans.configure.config import app_cfg, ROOT_DIR, REDUBB_STATUS_FILE,IPC_STATUS_FILE,logger
        from PySide6.QtCore import QSettings,QThreadPool
        from videotrans.task.clean_life import safe_quit
        os.chdir(ROOT_DIR)

        app_cfg.exit_soft = True
        app_cfg.current_status = 'stop'
        Path(REDUBB_STATUS_FILE).touch(exist_ok=True)
        Path(IPC_STATUS_FILE).touch(exist_ok=True)

        sets = QSettings("pyvideotrans", "settings")
        sets.setValue("windowSize", self.size())
        _forms=app_cfg.child_forms.values() if app_cfg.child_forms else []
        try:
            for w in _forms:
                if not w or not hasattr(w, 'hide'):
                    continue
                w.hide()
        except Exception as e:
            logger.exception(f'子窗口隐藏中出错 {e}', exc_info=True)

        if hasattr(self,'worker_threads'):
            for thread in self.worker_threads:
                if thread and thread.isRunning():
                    thread.requestInterruption()

            # 等待所有线程安全结束
            for thread in self.worker_threads:
                if thread and thread.isRunning():
                    thread.wait(3000)  # 等待3秒

        try:
            for w in _forms:
                if not w or not hasattr(w, 'close'):
                    continue
                w.close()
        except Exception as e:
            logger.exception(f'子窗口关闭中出错{e}', exc_info=True)

        safe_quit()
        QThreadPool.globalInstance().waitForDone(5000)

        if not self.is_restarting:
            return event.accept()


        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable] + sys.argv[1:])
        else:
            subprocess.Popen([sys.executable, sys.argv[0]] + sys.argv[1:])

        event.accept()
        os._exit(0)
