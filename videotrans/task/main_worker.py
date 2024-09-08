# -*- coding: utf-8 -*-
import copy
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.task.logs_worker import LogsWorker
from videotrans.task.trans_create import TransCreate
from videotrans.util.tools import set_process


class Worker(QThread):
    def __init__(self, *, parent=None, app_mode=None, txt=None, task_logs: LogsWorker = None, videolist: list = None):
        super().__init__(parent=parent)
        self.task_logs = task_logs
        self.video = None
        self.precent = 0
        self.app_mode = app_mode
        self.tasklist = {}
        self.uuidlist = []
        self.txt = txt
        self.is_batch = False
        # 存放处理好的 视频路径等信息
        self.videolist = videolist

    def run(self) -> None:
        # 重新初始化全局uuid表
        config.uuidlist = []

        # 如果是批量，则不允许中途暂停修改字幕
        if len(self.videolist) > 1 or self.app_mode == 'tiqu':
            self.is_batch = True
        config.params.update(
            {"is_batch": self.is_batch, 'subtitles': self.txt, 'app_mode': self.app_mode}
        )

        # 保存任务实例
        for it in self.videolist:
            if self._exit():
                return self.stop()
            self.task_logs.add(it['uuid'])
            if config.params['clear_cache'] and Path(it['target_dir']).is_dir():
                shutil.rmtree(it['target_dir'], ignore_errors=True)
            Path(it['target_dir']).mkdir(parents=True, exist_ok=True)
            self.uuidlist.append(it['uuid'])
            self.tasklist[it['uuid']] = TransCreate(copy.deepcopy(config.params), it)

        # 开始初始化任务并压入识别队列
        for video in self.tasklist.values():
            if self._exit():
                return self.stop()
            set_process(config.transobj['kaishichuli'], type="logs", uuid=video.uuid)
            # 压入识别队列开始执行
            config.prepare_queue.append(self.tasklist[video.uuid])
        # 批量进入等待
        return self.wait_end()

    def wait_end(self):
        # 开始等待任务执行完毕
        while len(self.uuidlist) > 0:
            if self._exit():
                return self.stop()
            uuid = self.uuidlist.pop(0)
            # uuid 不再当前任务列表中，已完成或出错结束，忽略
            if uuid not in self.tasklist:
                continue

            # 当前uuid 不在已执行完毕list中
            if uuid not in config.uuidlist:
                self.uuidlist.append(uuid)
            time.sleep(0.5)

        # 全部完成
        config.queue_mp4 = []
        config.uuidlist = []
        set_process("", type='end')

    def _exit(self):
        if config.exit_soft or config.current_status!='ing':
            return True
        return False
    # 暂停
    def stop(self):
        set_process("", type='end' if config.current_status=='ing' else 'stop')
        config.uuidlist = []
