import os
import platform
import shutil
import subprocess
import sys
import time
import getpass


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

    def kill_ffmpeg_processes(self):
        from videotrans.configure.config import logger

        current_user = getpass.getuser()
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    f'taskkill /F /FI "USERNAME eq {current_user}" /IM ffmpeg.exe',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.warning(f"taskkill returned: {result.returncode}, output: {result.stdout}")
            except Exception as e:
                logger.exception(f"Error using taskkill: {e}", exc_info=True)

            return

        try:
            result = subprocess.run(
                ['pkill', '-9', '-u', current_user, 'ffmpeg'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"pkill returned: {result.returncode}", exc_info=True)
        except Exception as e:
            logger.exception(f"Error using pkill: {e}", exc_info=True)

    def closeEvent(self, event):
        from videotrans.configure.config import app_cfg, ROOT_DIR, TEMP_ROOT

        app_cfg.exit_soft = True
        app_cfg.current_status = 'stop'
        self.hide()
        os.chdir(ROOT_DIR)
        self.cleanup_and_accept()

        time.sleep(4)
        try:
            shutil.rmtree(TEMP_ROOT, ignore_errors=True)
        except OSError:
            pass
        if not self.is_restarting:
            event.accept()
            return

        import subprocess
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable] + sys.argv[1:])
        else:
            subprocess.Popen([sys.executable, sys.argv[0]] + sys.argv[1:])

        event.accept()
        os._exit(0)

    def cleanup_and_accept(self):
        from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool
        from videotrans.configure.config import app_cfg, logger

        QCoreApplication.processEvents()
        sets = QSettings("pyvideotrans", "settings")
        sets.setValue("windowSize", self.size())
        try:
            for w in app_cfg.child_forms.values():
                if w and hasattr(w, 'hide'):
                    w.hide()
        except Exception as e:
            logger.exception(f'子窗口隐藏中出错 {e}', exc_info=True)

        for thread in self.worker_threads:
            if thread and thread.isRunning():
                thread.terminate()
                thread.wait(5000)

        try:
            for w in app_cfg.child_forms.values():
                if w and hasattr(w, 'close'):
                    w.close()
        except Exception as e:
            logger.exception(f'子窗口关闭中出错{e}', exc_info=True)

        QThreadPool.globalInstance().waitForDone(5000)
        self.kill_ffmpeg_processes()
