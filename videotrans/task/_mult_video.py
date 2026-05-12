import json
import time

from PySide6.QtCore import QThread,Signal
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate


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
        self.batch_nums=0
        try:
            self.batch_nums=int(float(settings.get('batch_nums',0)))
        except ValueError:
            pass


    def run(self):
        if app_cfg.exit_soft or app_cfg.current_status!='ing':return
        if self.batch_nums<1:
            for it in self.obj_list:
                # 压入识别队列开始执行
                app_cfg.rm_uuid(it['uuid'])
                app_cfg.prepare_queue.put_nowait(TransCreate(cfg=TaskCfgVTT(**self.cfg|it)))
            return

        logger.debug(f'批量翻译视频，每批次{self.batch_nums}个')
        _obj_list_split=[ self.obj_list[i:i+self.batch_nums] for i in range(0,len(self.obj_list),self.batch_nums)]
        for _it_split in _obj_list_split:
            trk_list=[]
            for it in _it_split:
                app_cfg.rm_uuid(it['uuid'])
                # 从停止队列中移出，以便重新开始
                trk=TransCreate(cfg=TaskCfgVTT(**self.cfg|it))
                app_cfg.prepare_queue.put_nowait(trk)
                trk_list.append(trk)
            #等待所有完成后，继续
            while 1:
                time.sleep(1)
                _this_batch_end=True
                for _trk in trk_list:
                    if not _trk.hasend and _trk.uuid not in app_cfg.stoped_uuid_set:
                        _this_batch_end=False
                        break
                if _this_batch_end:
                    #全部完成
                    break
