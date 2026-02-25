import json
import queue
import shutil
import time

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.configure.config import tr,settings,params,app_cfg

# 循环从日志队列中取出消息
class UUIDSignalThread(QThread):
    uito = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
    
    # 已停止的，删除掉日志队列
    def _remove_queue(self):
        for uuid in app_cfg.stoped_uuid_set:
            app_cfg.uuid_logs_queue.pop(uuid,None)

    def run(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.uito.emit(json.dumps(
                {"type": "ffmpeg", "text": tr("Please install ffmpeg")}))
        while 1:
            if app_cfg.exit_soft: return
            
            if len(self.parent.win_action.obj_list) < 1:
                if len(app_cfg.global_msg) > 0:
                    self.uito.emit(json.dumps(app_cfg.global_msg.pop(0)))
                self._remove_queue()
                if app_cfg.exit_soft: return
                time.sleep(0.1)
                continue
            # 找出未停止的任务
            uuid_list = [obj['uuid'] for obj in self.parent.win_action.obj_list if
                         obj['uuid'] not in app_cfg.stoped_uuid_set]
            # 全部结束
            if len(uuid_list) < 1:
                self.uito.emit(json.dumps({"type": "end"}))
                time.sleep(0.1)
                self._remove_queue()
                continue
            
            while len(uuid_list) > 0:
                if app_cfg.exit_soft: return
                try:
                    uuid = uuid_list.pop(0)
                except IndexError:
                    time.sleep(0.1)
                    continue
                # 该任务已停止
                if uuid in app_cfg.stoped_uuid_set:
                    app_cfg.uuid_logs_queue.pop(uuid,None)
                    continue
                if app_cfg.exit_soft: return
                try:
                    q = app_cfg.uuid_logs_queue.get(uuid)
                    if not q:
                        continue
                    data = q.get_nowait()
                    if data:
                        self.uito.emit(json.dumps(data))
                except Exception:
                    pass
                finally:
                    if app_cfg.exit_soft: return
