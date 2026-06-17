import time
from typing import List

from PySide6.QtCore import QThread
from videotrans.configure.config import settings, app_cfg, logger
from videotrans.task.taskcfg import TaskCfgVTT, InputFile
from videotrans.task.trans_create import TransCreate


class MultVideo(QThread):
    def __init__(self, *,
                 parent,
                 cfg,
                 input_file_list:List[InputFile]
                 ):
        super().__init__(parent=parent)
        self.cfg = cfg
        # 存放处理好的 视频路径等信息
        self.input_file_list = input_file_list
        self.batch_nums = 0
        try:
            self.batch_nums = int(float(settings.get('batch_nums', 0)))
        except (ValueError,TypeError):
            pass

    def run(self):
        if app_cfg.exit_soft or app_cfg.current_status != 'ing': return
        if self.batch_nums < 1:
            logger.debug(f'批量翻译模式并不限制数量')
            for it in self.input_file_list:
                # 压入识别队列开始执行
                app_cfg.rm_uuid(it['uuid'])
                app_cfg.prepare_queue.put_nowait(TransCreate(cfg=TaskCfgVTT(**self.cfg | it,batch=True)))
            return
        logger.debug(f'批量翻译模式，每批次 {self.batch_nums}')
        _obj_list_split = [self.input_file_list[i:i + self.batch_nums] for i in range(0, len(self.input_file_list), self.batch_nums)]
        for i,_it_split in enumerate(_obj_list_split):
            logger.debug(f'进入第 {i} 批次，当前批次数量:{len(_it_split)}')
            trk_list = []
            for it in _it_split:
                app_cfg.rm_uuid(it['uuid'])
                trk = TransCreate(cfg=TaskCfgVTT(**self.cfg | it,batch=True,batch_size=self.batch_nums))
                app_cfg.prepare_queue.put_nowait(trk)
                trk_list.append(trk)

            while 1:
                time.sleep(1)
                _this_batch_end = True
                for _trk in trk_list:
                    if not _trk.hasend and _trk.uuid not in app_cfg.stoped_uuid_set:
                        _this_batch_end = False
                        break
                if _this_batch_end:
                    break
