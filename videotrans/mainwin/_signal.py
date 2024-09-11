import json
import time

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


class  UUIDSignalThread(QThread):
    uito=Signal(str)

    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.parent=parent

    def run(self):
        while 1:
            if config.exit_soft:
                return
            if len(self.parent.util.obj_list)<1:
                time.sleep(1)
                continue
            # 找出未停止的
            uuid_list=[obj['uuid'] for obj in self.parent.util.obj_list if obj['uuid'] not in config.stoped_uuid_set]
            # 全部结束
            if len(uuid_list)<1:
                self.uito.emit(json.dumps({"type":"end"}))
                time.sleep(1)
                continue
            while len(uuid_list)>0:
                uuid=uuid_list.pop(0)
                if config.exit_soft:
                    return
                if uuid in config.stoped_uuid_set:
                    continue
                try:
                    q=config.uuid_logs_queue.get(uuid)
                    if not q:
                        continue
                    data=q.get(block=False)
                    if data:
                        self.uito.emit(json.dumps(data))
                except Exception:
                    pass
            time.sleep(0.1)