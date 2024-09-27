# -*- coding: utf-8 -*-
import copy
import json
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.util.tools import set_process


class Worker(QThread):
    uito = Signal(str)
    def __init__(self, *, parent=None, app_mode=None, txt=None, obj_list: list = None):
        super().__init__(parent=parent)
        self.video = None
        self.precent = 0
        self.app_mode = app_mode
        self.tasklist = {}
        # 等待执行的任务uuid
        self.wait_uuid_list = []
        self.txt = txt
        self.is_batch = False
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list

    def run(self) -> None:
        # 如果是批量，则不允许中途暂停修改字幕
        if len(self.obj_list) > 1 or self.app_mode in ['tiqu','biaozhun_jd']:
            self.is_batch = True
        config.params.update(
            {'subtitles': self.txt, 'app_mode': self.app_mode}
        )

        # 保存任务实例
        for it in self.obj_list:
            if self._exit():
                return
            if config.params['clear_cache'] and Path(it['target_dir']).is_dir():
                shutil.rmtree(it['target_dir'], ignore_errors=True)
            Path(it['target_dir']).mkdir(parents=True, exist_ok=True)
            self.wait_uuid_list.append(it['uuid'])
            trk = TransCreate(copy.deepcopy(config.params), it)

            if not self.is_batch:
                return self._sole(trk)

            self.tasklist[it['uuid']]=trk
        # 开始初始化任务并压入识别队列
        for video in self.tasklist.values():
            if self._exit():
                return
            set_process(text=config.transobj['kaishichuli'], uuid=video.uuid)
            # 压入识别队列开始执行
            config.prepare_queue.append(self.tasklist[video.uuid])
        # 开始等待任务执行完毕
        while len(self.wait_uuid_list) > 0:
            if self._exit():
                return
            uuid = self.wait_uuid_list.pop(0)
            # uuid 不再当前任务列表中，已完成或出错结束，忽略
            if uuid not in self.tasklist:
                continue

            # 当前uuid 不在已执行完毕list中，重新插入继续执行
            if uuid not in config.stoped_uuid_set:
                self.wait_uuid_list.append(uuid)
            time.sleep(0.5)

        # 全部完成
        config.queue_mp4 = []

    def _sole(self,trk):
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
        return

    def _post(self,text,type='logs'):
        self.uito.emit(json.dumps({"text":text,"type":type}))

    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False

