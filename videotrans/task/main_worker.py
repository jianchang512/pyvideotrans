# -*- coding: utf-8 -*-
import copy
import os
import shutil
import time
from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools
from videotrans.util.tools import set_process, delete_temp, send_notification
from pathlib import Path


class Worker(QThread):
    def __init__(self, *, parent=None, app_mode=None, txt=None):
        super().__init__(parent=parent)
        self.video = None
        self.app_mode = app_mode
        self.tasklist = {}
        self.tasknums = 0
        self.txt = txt

    def srt2audio(self):
        try:
            config.btnkey = "srt2wav"
            # 添加进度按钮
            set_process('srt2wav', 'add_process', btnkey="srt2wav")
            config.params.update({"is_batch": False, 'subtitles': self.txt, 'app_mode': self.app_mode})
            try:
                self.video = TransCreate(copy.deepcopy(config.params), None)
                set_process(config.transobj['kaishichuli'], btnkey="srt2wav")
                self.video.prepare()
            except Exception as e:
                raise Exception(f'{config.transobj["yuchulichucuo"]}:'+str(e))
            try:
                self.video.dubbing()
            except Exception as e:
                raise Exception(f'{config.transobj["peiyinchucuo"]}:'+str(e))
            # 成功完成
            config.params['line_roles'] = {}
            set_process(f"{self.video.target_dir}##srt2wav", 'succeed', btnkey="srt2wav")
            send_notification(config.transobj["zhixingwc"], f'"subtitles -> audio"')
            # 全部完成
            set_process("", 'end')
        except Exception as e:
            set_process(f"{str(e)}", 'error')
            send_notification("Error", str(e))
        finally:
            pass

    def run(self) -> None:
        # 字幕配音
        if self.app_mode == 'peiyin':
            return self.srt2audio()

        # 多个视频处理
        videolist = []
        for it in config.queue_mp4:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            # 格式化每个视频信息
            obj_format = tools.format_video(it.replace('\\', '/'), config.params['target_dir'])
            videolist.append(obj_format)
            # 添加进度按钮 unid
            set_process(obj_format['unid'], 'add_process', btnkey=obj_format['unid'])
        # 如果是批量，则不允许中途暂停修改字幕
        config.params.update(
            {"is_batch": True if len(videolist) > 1 else False, 'subtitles': self.txt, 'app_mode': self.app_mode})
        # 开始
        for it in videolist:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            if Path(it['raw_name']).exists() and not Path(it['source_mp4']).exists():
                shutil.copy2(it['raw_name'], it['source_mp4'])
            self.tasklist[it['unid']] = TransCreate(copy.deepcopy(config.params), it)
            set_process(it['raw_basename'], 'logs', btnkey=it['unid'])

        self.tasknums = len(self.tasklist.keys())

        # 预先处理
        for idx, video in self.tasklist.items():
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            try:
                video.prepare()
                set_process(config.transobj['kaishichuli'], btnkey=video.btnkey)
                config.regcon_queue.append(self.tasklist[video.btnkey])
            except Exception as e:
                set_process(f'{config.transobj["yuchulichucuo"]}:' + str(e), 'error', btnkey=video.btnkey)
        try:
            config.unidlist = []
            while 1:
                for idx, video in self.tasklist.items():
                    if config.exit_soft or config.current_status != 'ing':
                        return self.stop()
                    if video.compose_end and video.btnkey not in config.unidlist:
                        config.unidlist.append(video.btnkey)
                        video.move_at_end()
                        send_notification(config.transobj["zhixingwc"], f'{video.obj["raw_basename"]}')
                        if len(config.queue_mp4) > 0:
                            config.queue_mp4.pop(0)
                    time.sleep(1)
                if len(config.unidlist) == self.tasknums:
                    break
        except Exception as e:
            print(f'{e=}#######################')
        # 全部完成
        set_process("", 'end')
        time.sleep(3)
        delete_temp()

    def stop(self):
        set_process("", 'stop')
        self.tasklist = {}
        self.tasknums = 0
