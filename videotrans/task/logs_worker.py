# 从日志队列获取日志
import json

from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.configure.config import queue_logs


class LogsWorker(QThread):
    post_logs = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        while True:
            if config.exit_soft:
                return
            try:
                obj = queue_logs.get(True, 0.5)
                if "type" not in obj:
                    obj['type'] = 'logs'
                if config.current_status!='ing' and obj['type'] in ['logs','error','stop','end','succeed']:
                    continue
                self.post_logs.emit(json.dumps(obj))
            except Exception as e:
                pass
