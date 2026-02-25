import shutil,json
from pathlib import Path

from PySide6.QtCore import QThread,Signal

from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools


class MultVideo(QThread):
    uito = Signal(str)
    def __init__(self, *,
                 parent,
                 cfg,
                 obj_list
                 ):
        super().__init__(parent=parent)
        self.cfg = cfg
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list
        self.batch_single=bool(settings.get('batch_single'))

    def run(self):
        for it in self.obj_list:
            if app_cfg.exit_soft:return
            if self.cfg['clear_cache'] and Path(it['target_dir']).is_dir():
                shutil.rmtree(it['target_dir'], ignore_errors=True)
            Path(it['target_dir']).mkdir(parents=True, exist_ok=True)
            try:
                trk = TransCreate(cfg=TaskCfgVTT(**self.cfg|it))
                if self.batch_single:
                    trk.prepare()
                    trk.recogn()
                    trk.diariz()
                    trk.trans()
                    trk.dubbing()
                    trk.align()
                    trk.assembling()
                    trk.task_done()
                    self.uito.emit(json.dumps({"text": tr('Succeed'), "type": 'succeed', 'uuid': it['uuid']}))
                else:
                    # 压入识别队列开始执行
                    app_cfg.prepare_queue.put_nowait(trk)
            except Exception as e:
                if self.batch_single:
                    self.uito.emit(json.dumps({"text": str(e), "type": "error", 'uuid': it['uuid']}))
                else:
                    tools.set_process(text=str(e),type="error",uuid=it['uuid'])

