import json
import time

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config


class SignThread(QThread):
    uito = Signal(str)

    def __init__(self, uuid_list=None, parent=None):
        super().__init__(parent=parent)
        self.uuid_list = uuid_list

    def post(self, jsondata):
        self.uito.emit(json.dumps(jsondata))

    def run(self):
        length = len(self.uuid_list)
        while 1:
            if config.exit_soft: return
            if len(self.uuid_list) == 0:
                self.post({"type": "end"})
                time.sleep(0.1)
                return

            for uuid in self.uuid_list:
                if config.exit_soft: return
                if uuid in config.stoped_uuid_set:
                    try:
                        self.uuid_list.remove(uuid)
                    except ValueError:
                        pass
                    continue
                q = config.uuid_logs_queue.get(uuid)
                if not q:
                    continue
                try:
                    if q.empty():
                        time.sleep(0.1)
                        continue
                    data = q.get(block=True,timeout=0.1)
                    if not data:
                        continue
                    self.post(data)
                    if data['type'] in ['error', 'succeed']:
                        self.uuid_list.remove(uuid)
                        self.post(
                            {"type": "jindu", "text": f'{int((length - len(self.uuid_list)) * 100 / length)}%'})
                        config.stoped_uuid_set.add(uuid)
                        config.uuid_logs_queue.pop(uuid,None)
                    q.task_done()
                except Exception:
                    pass
