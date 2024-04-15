# 从日志队列获取日志
import json
from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.configure.config import queuebox_logs

class LogsWorker(QThread):
    post_logs = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        while True:
            if config.exit_soft:
                return
            try:
                obj = queuebox_logs.get(True, 1)
                if "type" not in obj:
                    obj['type'] = 'logs'
                self.post_logs.emit(json.dumps(obj))
            except Exception as e:
                pass
