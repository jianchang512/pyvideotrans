# 执行单个视频翻译任务时 暂停等待
import copy
import json
import shutil
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QThread, Signal, QObject

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools


class Worker(QThread):
    uito = Signal(str)

    def __init__(self, *,
                 parent: Optional[QObject] = None,
                 app_mode: Optional[str] = None,
                 txt: Optional[str] = None,
                 obj_list: Optional[List[Dict[str, Any]]] = None,
                 cfg: Optional[Dict[str, Any]] = None):
        super().__init__(parent=parent)
        self.app_mode = app_mode
        self.cfg = cfg

        self.txt = txt
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list
        self.uuid = None

    def run(self) -> None:
        obj=self.obj_list[0]
        if self.cfg['clear_cache'] and Path(obj['target_dir']).is_dir():
            shutil.rmtree(obj['target_dir'], ignore_errors=True)
        Path(obj['target_dir']).mkdir(parents=True, exist_ok=True)
        try:
            trk = TransCreate(cfg=copy.deepcopy(self.cfg), obj=obj)
            self.uuid = trk.uuid
            config.task_countdown = 0
            trk.prepare()
            self._post(text=trk.cfg['source_sub'], type='edit_subtitle_source')
            trk.recogn()
            if trk.shoud_trans:
                if tools.vail_file(trk.cfg['target_sub']):
                    if tools.vail_file(trk.cfg['source_sub']):
                        self._post(text=Path(trk.cfg['source_sub']).read_text(encoding='utf-8'),
                                   type='replace_subtitle')
                    self._post(text=trk.cfg['target_sub'], type="edit_subtitle_target")
                else:
                    time.sleep(1)
                    countdown_sec = int(float(config.settings.get('countdown_sec', 1)))
                    config.task_countdown = countdown_sec
                    # 等待编辑原字幕后翻译,允许修改字幕
                    self._post(text=Path(trk.cfg['source_sub']).read_text(encoding='utf-8'), type='replace_subtitle')
                    self._post(text=f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}", type='show_djs')
                    while config.task_countdown > 0:
                        if self._exit():
                            return
                        time.sleep(1)
                        config.task_countdown -= 1
                        if config.task_countdown > 0 and config.task_countdown <= countdown_sec:
                            self._post(text=f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}",
                                       type='show_djs')
                    self._post(text='', type='timeout_djs')
                    # 等待字幕更新完毕
                    config.task_countdown = 10
                    while config.task_countdown > 0:
                        time.sleep(1)
                        break
                    self._post(text=trk.cfg['target_sub'], type="edit_subtitle_target")
                    trk.trans()

            if trk.shoud_dubbing:
                countdown_sec = int(float(config.settings.get('countdown_sec', 1)))
                config.task_countdown = countdown_sec
                self._post(text=Path(trk.cfg['target_sub']).read_text(encoding='utf-8'), type='replace_subtitle')
                self._post(
                    text=f"{config.task_countdown}{config.transobj['zidonghebingmiaohou']}",
                    type='show_djs')
                while config.task_countdown > 0:
                    if self._exit():
                        return
                    # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                    time.sleep(1)
                    # 倒计时中
                    config.task_countdown -= 1
                    if config.task_countdown > 0 and config.task_countdown <= countdown_sec:
                        self._post(
                            text=f"{config.task_countdown}{config.transobj['zidonghebingmiaohou']}",
                            type='show_djs')
                # 禁止修改字幕
                self._post(text='', type='timeout_djs')
                # 等待字幕更新完毕
                config.task_countdown = 10
                while config.task_countdown > 0:
                    time.sleep(1)
                    break

            trk.dubbing()
            trk.align()
            trk.assembling()
            trk.task_done()
        except Exception as e:
            self._post(text=str(e), type='error')

    def _post(self, text, type='logs'):
        try:
            self.uito.emit(json.dumps({"text": text, "type": type, 'uuid': self.uuid}))
        except:
            pass

    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False
