# 从日志队列获取日志
import json
from PyQt5.QtCore import QThread, pyqtSignal
from videotrans.configure.config import queuebox_logs

class LogsWorker(QThread):
    post_logs = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        while True:
            try:
                obj = queuebox_logs.get(True, 1)
                if "type" not in obj:
                    obj['type'] = 'logs'
                self.post_logs.emit(json.dumps(obj))
            except Exception as e:
                pass
