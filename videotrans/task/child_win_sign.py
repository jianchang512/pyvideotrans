from PySide6.QtCore import QThread, Signal

from videotrans.configure.config import app_cfg
from videotrans.configure.signal_hub import SignalHub
from videotrans.task.taskcfg import SignMsg


class SignThread(QThread):
    uito = Signal(object)

    def __init__(self, uuid_list=None, parent=None):
        super().__init__(parent=parent)
        self.uuid_list = uuid_list

    def post(self, jsondata:SignMsg):
        self.uito.emit(jsondata)

    def _on_message(self, uuid, d:SignMsg):
        if uuid not in self.uuid_list : return
        self.uito.emit(d)
        if d['type'] in ['error', 'succeed']:
            self.uuid_list.remove(uuid)
            self.uito.emit(SignMsg(**{
                "type": "jindu",
                "text": f'{int((self.total - len(self.uuid_list)) * 100 / self.total)}%'
            }))
            app_cfg.stoped_uuid_set.add(uuid)
            if not self.uuid_list:
                self.uito.emit(SignMsg(**{"type": "end"}))

    def run(self):
        self.total = len(self.uuid_list)
        SignalHub.instance().new_message.connect(self._on_message)
        # exec() 保持线程事件循环运行（让 queued connection 能够传递）
        self.exec()
