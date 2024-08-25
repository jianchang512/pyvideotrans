# -*- coding: utf-8 -*-
import copy
import os
import shutil
import time
from PySide6.QtCore import QThread

from videotrans import translator
from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools
from videotrans.util.tools import set_process, send_notification
from pathlib import Path
import re
import threading


class Worker(QThread):
    def __init__(self, *, parent=None, app_mode=None, txt=None):
        super().__init__(parent=parent)
        self.video = None
        self.precent = 0
        self.app_mode = app_mode
        self.tasklist = {}
        self.unidlist = []
        self.txt = txt
        self.is_batch = False


    def run(self) -> None:
        # 多个视频处理
        videolist = []
        # 重新初始化全局unid表
        config.unidlist = []
        # 全局错误信息初始化
        config.errorlist = {}
        # 初始化本地 unidlist 表
        self.unidlist = []
        for it in config.queue_mp4:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            # 格式化每个视频信息
            obj_format = tools.format_video(it.replace('\\', '/'), config.params['target_dir'])
            if config.params['clear_cache'] and Path(obj_format['output']).is_dir():
                try:
                    shutil.rmtree(obj_format['output'])
                except Exception:
                    pass
                else:
                    Path(obj_format['output']).mkdir(parents=True, exist_ok=True)
            videolist.append(obj_format)
            self.unidlist.append(obj_format['unid'])
            # 添加进度按钮 unid
            set_process(obj_format['output'], type='add_process', btnkey=obj_format['unid'])
        # 如果是批量，则不允许中途暂停修改字幕
        if len(videolist) > 1 or self.app_mode=='tiqu':
            self.is_batch = True
        config.params.update(
            {"is_batch": self.is_batch, 'subtitles': self.txt, 'app_mode': self.app_mode})
        # 开始
        for it in videolist:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            self.tasklist[it['unid']] = TransCreate(copy.deepcopy(config.params), it)
            set_process(it['raw_basename'], type='logs', btnkey=it['unid'])

        # 开始初始化任务
        for idx, video in self.tasklist.items():
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            try:
                set_process(config.transobj['kaishichuli'], type="logs",btnkey=video.init['btnkey'])
                video.prepare()
            except Exception as e:
                err = f'{config.transobj["yuchulichucuo"]}:' + str(e)
                config.logger.exception(err)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, type='error', btnkey=video.init['btnkey'])
                self.unidlist.remove(video.init['btnkey'])
                continue
            # 压入识别队列开始执行
            config.regcon_queue.append(self.tasklist[video.init['btnkey']])
        # 批量进入等待
        return self.wait_end()

    def wait_end(self):
        # 开始等待任务执行完毕
        while len(self.unidlist) > 0:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            unid = self.unidlist.pop(0)
            if unid not in self.tasklist:
                continue

            # 当前 video 执行完毕
            if unid in config.unidlist:
                pass
            else:
                # 未结束重新插入
                self.unidlist.append(unid)
            time.sleep(0.5)
        # 全部完成

        set_process("", type='end')
        tools._unlink_tmp()
        config.queue_mp4 = []
        config.unidlist = []

    def stop(self):
        set_process("", type='stop')
        tools._unlink_tmp()
        config.queue_mp4 = []
        config.unidlist = []
