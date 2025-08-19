import copy
import shutil
from pathlib import Path

from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools


class MultVideo(QThread):
    def __init__(self, *,
                 parent,
                 cfg,
                 obj_list
                 ):
        super().__init__(parent=parent)
        self.cfg = cfg
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list

    def run(self):
        for it in self.obj_list:
            if self.cfg['clear_cache'] and Path(it['target_dir']).is_dir():
                shutil.rmtree(it['target_dir'], ignore_errors=True)
            Path(it['target_dir']).mkdir(parents=True, exist_ok=True)
            trk = TransCreate(cfg=copy.deepcopy(self.cfg), obj=it)
            tools.set_process(text=config.transobj['kaishichuli'], uuid=it['uuid'])
            # 压入识别队列开始执行
            config.prepare_queue.append(trk)
