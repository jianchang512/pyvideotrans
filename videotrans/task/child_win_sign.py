import json
import time

from PySide6.QtCore import QThread, Signal

from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure.signal_hub import SignalHub


class SignThread(QThread):
    uito = Signal(object)

    def __init__(self, uuid_list=None, parent=None):
        super().__init__(parent=parent)
        self.uuid_list = uuid_list

    def post(self, jsondata):
        self.uito.emit(jsondata)


    def _on_message(self, uuid, json_str):
        if uuid not in self.uuid_list:
            return
        d = json.loads(json_str) if isinstance(json_str,str) else json_str
        self.uito.emit(d)
        if d['type'] in ['error', 'succeed']:
            self.uuid_list.remove(uuid)
            self.uito.emit({
                "type": "jindu",
                "text": f'{int((self.total - len(self.uuid_list)) * 100 / self.total)}%'
            })
            app_cfg.stoped_uuid_set.add(uuid)
            # app_cfg.uuid_logs_queue.pop(uuid, None)
            if not self.uuid_list:
                self.uito.emit({"type": "end"})

    def run(self):
        self.total = len(self.uuid_list)
        SignalHub.instance().new_message.connect(self._on_message)
        # exec() 保持线程事件循环运行（让 queued connection 能够传递）
        self.exec()