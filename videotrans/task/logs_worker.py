# 从日志队列获取日志
import json
import time
from queue import Queue

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


class LogsWorker(QThread):
    post_logs = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # global 队列用于接收全局数据
        self.uuid_set = {'global'}

    # 将uuid加入 self.uuid_set
    def add(self, uuid):
        self.uuid_set.add(uuid)

    # 将uuid从self.uuid_set中删除
    def remove(self, uuid):
        try:
            self.uuid_set.remove(uuid)
        except KeyError:
            pass
        if uuid in config.queue_dict:
            try:
                del config.queue_dict[uuid]
            except Exception:
                pass

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            # 获取进度队列数据发送
            for uuid in self.uuid_set:
                if config.current_status != 'ing':
                    if uuid in config.queue_dict:
                        del config.queue_dict[uuid]
                    continue
                q: Queue = config.queue_dict.get(uuid, None)
                if q:
                    try:
                        obj = q.get(block=False)
                        if obj and obj['type'] != 'stop' and config.current_status == 'ing':
                            self.post_logs.emit(json.dumps(obj))
                    except:
                        pass
            time.sleep(0.1)
