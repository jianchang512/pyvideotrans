# 执行单个视频翻译任务时 暂停等待
import copy
import json
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate

class Worker(QThread):
    uito = Signal(str)
    def __init__(self, *, parent=None, app_mode=None, txt=None, obj = None):
        super().__init__(parent=parent)
        self.app_mode = app_mode
        # 等待执行的任务uuid
        self.txt = txt
        # 存放处理好的 视频路径等信息
        self.obj = obj

    def run(self) -> None:
        # 如果是批量，则不允许中途暂停修改字幕
        config.params.update(
            {'subtitles': self.txt, 'app_mode': self.app_mode}
        )
        if config.params['clear_cache'] and Path(self.obj['target_dir']).is_dir():
            shutil.rmtree(self.obj['target_dir'], ignore_errors=True)
        Path(self.obj['target_dir']).mkdir(parents=True, exist_ok=True)
        trk = TransCreate(copy.deepcopy(config.params), self.obj)
        config.task_countdown=0
        trk.prepare()
        trk.recogn()
        if trk.shoud_trans:
            time.sleep(1)
            countdown_sec = int(config.settings['countdown_sec'])
            config.task_countdown = countdown_sec
            # 设置secwin中wait_subtitle为原始语言字幕文件
            self._post(text=trk.config_params['source_sub'], type='set_source_sub')
            # 等待编辑原字幕后翻译,允许修改字幕
            self._post(text=config.transobj["xiugaiyuanyuyan"], type='edit_subtitle_source')
            self._post(text=Path(trk.config_params['source_sub']).read_text(encoding='utf-8'),
                       type='replace_subtitle')
            self._post(text=f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}", type='show_djs')
            while config.task_countdown > 0:
                if self._exit():
                    return
                time.sleep(1)
                config.task_countdown -= 1
                if config.task_countdown > 0 and config.task_countdown <= countdown_sec:
                    self._post(text=f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}",
                               type='show_djs')
            # 禁止修改字幕
            self._post(text='', type='timeout_djs')
            trk.trans()
            time.sleep(1)

        if trk.shoud_dubbing:
            countdown_sec = int(config.settings['countdown_sec'])
            config.task_countdown = countdown_sec
            self._post(text=trk.config_params['target_sub'], type='set_target_sub')
            self._post(text=config.transobj["xiugaipeiyinzimu"], type="edit_subtitle_target")
            self._post(text=Path(trk.config_params['target_sub']).read_text(encoding='utf-8'),
                       type='replace_subtitle')
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
            trk.dubbing()
            time.sleep(1)
        trk.align()
        trk.assembling()
        trk.task_done()


    def _post(self,text,type='logs'):
        self.uito.emit(json.dumps({"text":text,"type":type}))

    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False

