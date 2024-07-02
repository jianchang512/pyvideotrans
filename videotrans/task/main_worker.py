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

    # 单个字幕配音
    def srt2audio(self):
        # 添加进度按钮
        self.is_batch = False
        set_process('srt2wav', 'add_process', btnkey="srt2wav")
        config.params.update({"is_batch": False, 'subtitles': self.txt, 'app_mode': self.app_mode})
        try:
            self.video = TransCreate(copy.deepcopy(config.params))
        except Exception as e:
            set_process(str(e), 'error', btnkey="srt2wav")
            return

        try:
            set_process(config.transobj['kaishichuli'], btnkey="srt2wav")
            self.video.prepare()
        except Exception as e:
            set_process(f'{config.transobj["yuchulichucuo"]}:' + str(e), 'error', btnkey="srt2wav")
            return

        try:
            self.video.dubbing()
        except Exception as e:
            set_process(f"{str(e)}", 'error', btnkey="srt2wav")
            return
        # 成功完成
        config.params['line_roles'] = {}
        set_process(f"{self.video.init['target_dir']}##srt2wav", 'succeed', btnkey="srt2wav")
        send_notification(config.transobj["zhixingwc"], f'"subtitles -> audio"')
        # 全部完成
        set_process("", 'end')

    # 字幕嵌入视频
    def hebing(self):
        self.is_batch = False
        set_process('hebing', 'add_process', btnkey="hebing")
        self.precent = 1
        it = config.queue_mp4.pop()
        print(f'{it=}')
        obj_format = tools.format_video(it.replace('\\', '/'), config.params['target_dir'])
        if obj_format['linshi_output'] != obj_format['output']:
            shutil.copy2(it, obj_format['source_mp4'])
        target_dir_mp4 = obj_format['output'] + f"/{obj_format['raw_noextname']}.mp4"
        if config.params['only_video']:
            target_dir_mp4 = os.path.dirname(obj_format['output']) + f"/{obj_format['raw_noextname']}.mp4"
            print(f'{target_dir_mp4=}')
            shutil.rmtree(obj_format['output'],ignore_errors=True)

        video_info = tools.get_video_info(obj_format['source_mp4'])
        self.precent = 10
        # 设定最终需输出的视频编码
        video_code_num = int(config.settings['video_codec'])
        video_codec = 'h264' if video_code_num == 264 else 'hevc'
        copy = False
        if video_info['video_codec_name'] == video_codec and obj_format['ext'].lower() == 'mp4':
            copy = True
        hard_srt = "tmp.srt"
        hard_srt_path = config.rootdir + '/' + hard_srt
        with open(hard_srt_path, 'w', encoding='utf-8') as f:
            f.write(self.txt)
        os.chdir(config.rootdir)
        try:
            if config.params['subtitle_type'] in [0, 1, 3]:
                # 硬字幕仅名字 需要和视频在一起
                tools.runffmpeg([
                    "-y",
                    "-i",
                    obj_format['source_mp4'],
                    "-c:v",
                    f"libx{video_code_num}",
                    "-c:a",
                    "aac",
                    "-vf",
                    f"subtitles={hard_srt}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset'],
                    target_dir_mp4,
                ])
            else:
                # 软字幕
                print(f"{config.params['source_language']=}")
                subtitle_language = translator.get_subtitle_code(show_target=config.params['source_language'])
                subtitle_language = "chi" if not subtitle_language or subtitle_language == '-' else subtitle_language
                print(f'{subtitle_language=}')
                tools.runffmpeg([
                    "-y",
                    "-i",
                    obj_format['source_mp4'],
                    "-i",
                    hard_srt_path,
                    "-c:v",
                    'copy' if copy else f"libx{video_code_num}",
                    "-c:a",
                    'copy' if copy else "aac",
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={subtitle_language}",
                    target_dir_mp4
                ])
                if not config.params['only_video']:
                    shutil.copy2(hard_srt_path, f'{obj_format["output"]}/{obj_format["raw_noextname"]}.srt')
            self.precent = 90
        except Exception as e:
            set_process(str(e), 'error', btnkey="hebing")
        try:
            os.unlink(hard_srt_path)
        except Exception:
            pass
        self.precent = 100
        set_process(f"{obj_format['output']}##hebing", 'succeed', btnkey="hebing")
        send_notification(config.transobj["zhixingwc"], target_dir_mp4)
        # 全部完成
        set_process("", 'end')
        return None

    def run(self) -> None:
        # 字幕配音
        if self.app_mode == 'peiyin':
            return self.srt2audio()
        if self.app_mode == 'hebing':
            return self.hebing()
        # 提取字幕模式、标准模式
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
            target_dir_mp4 = obj_format['output'] + f"/{obj_format['raw_noextname']}.mp4"
            if config.params['clear_cache'] and Path(obj_format['output']).is_dir():
                try:
                    shutil.rmtree(obj_format['output'])
                except Exception:
                    pass
                else:
                    Path(obj_format['output']).mkdir(parents=True, exist_ok=True)

            if len(target_dir_mp4) >= 250:
                set_process(config.transobj['chaochu255'] + "\n\n" + it, 'alert')
                self.stop()
                return
            if re.search(r'[\&\+\:\?\|]+', it[2:]):
                set_process(config.transobj['teshufuhao'] + "\n\n" + it, 'alert')
                self.stop()
                return

            videolist.append(obj_format)
            self.unidlist.append(obj_format['unid'])
            # 添加进度按钮 unid
            set_process(obj_format['unid'], 'add_process', btnkey=obj_format['unid'])
        # 如果是批量，则不允许中途暂停修改字幕
        if len(videolist) > 1 and config.settings['cors_run']:
            self.is_batch = True
        config.params.update(
            {"is_batch": self.is_batch, 'subtitles': self.txt, 'app_mode': self.app_mode})
        # 开始
        for it in videolist:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            # 需要移动mp4位置
            if tools.vail_file(it['raw_name']) and not tools.vail_file(it['source_mp4']):
                shutil.copy2(it['raw_name'], it['source_mp4'])
            self.tasklist[it['unid']] = TransCreate(copy.deepcopy(config.params), it)
            set_process(it['raw_basename'], 'logs', btnkey=it['unid'])

        # 开始初始化任务
        for idx, video in self.tasklist.items():
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            try:
                set_process(config.transobj['kaishichuli'], btnkey=video.init['btnkey'])
                video.prepare()
            except Exception as e:
                err = f'{config.transobj["yuchulichucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                if self.is_batch:
                    self.unidlist.remove(video.init['btnkey'])
                continue

            if self.is_batch:
                # 压入识别队列开始执行
                config.regcon_queue.append(self.tasklist[video.init['btnkey']])
                continue
            # 非批量并发
            try:
                if config.exit_soft or config.current_status != 'ing':
                    return self.stop()
                video.recogn()
            except Exception as e:
                err = f'{config.transobj["shibiechucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                continue
            try:
                if config.exit_soft or config.current_status != 'ing':
                    return self.stop()
                video.trans()
            except Exception as e:
                err = f'{config.transobj["fanyichucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                continue
            try:
                if config.exit_soft or config.current_status != 'ing':
                    return self.stop()
                video.dubbing()
            except Exception as e:
                err = f'{config.transobj["peiyinchucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                continue
            try:
                if config.exit_soft or config.current_status != 'ing':
                    return self.stop()
                video.hebing()
            except Exception as e:
                err = f'{config.transobj["hebingchucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                continue
            try:
                if config.exit_soft or config.current_status != 'ing':
                    return self.stop()
                video.move_at_end()
            except Exception as e:
                err = f'{config.transobj["hebingchucuo"]}:' + str(e)
                config.errorlist[video.init['btnkey']] = err
                set_process(err, 'error', btnkey=video.init['btnkey'])
                send_notification(err, f'{video.obj["raw_basename"]}')
                continue
            # else:
            #     send_notification("Succeed", f'{video.obj["raw_basename"]}')
        # 批量进入等待
        if self.is_batch:
            return self.wait_end()
        # 非批量直接结束
        config.queue_mp4 = []
        set_process("", 'end')
        # self._unlink_tmp()
        # self.tasklist = {}

    def _unlink_tmp(self):
        if not os.path.isdir(config.TEMP_DIR):
            return
        for it in os.listdir(config.TEMP_DIR):
            if os.path.isfile(config.TEMP_DIR + f"/{it}"):
                Path(config.TEMP_DIR + f"/{it}").unlink(missing_ok=True)
            else:
                shutil.rmtree(config.TEMP_DIR + f"/{it}", ignore_errors=True)

    def wait_end(self):
        # 开始等待任务执行完毕
        while len(self.unidlist) > 0:
            if config.exit_soft or config.current_status != 'ing':
                return self.stop()
            unid = self.unidlist.pop(0)
            if unid not in self.tasklist:
                continue
            video = self.tasklist[unid]
            # 当前 video 执行完毕
            if unid in config.unidlist:
                pass
                # 成功完成
                # if unid  in config.errorlist and config.errorlist[unid]:
                # send_notification("Succeed", f'{video.obj["raw_basename"]}')
                # if len(config.queue_mp4) > 0:
                # config.queue_mp4.pop(0)
                # else:
                # send_notification(config.errorlist[unid], f'{video.obj["raw_basename"]}')
            else:
                # 未结束重新插入
                self.unidlist.append(unid)
            time.sleep(0.5)
        # 全部完成
        config.queue_mp4 = []

        set_process("", 'end')
        self._unlink_tmp()
        # self.tasklist = {}

    def stop(self):
        set_process("", 'stop')
        config.queue_mp4 = []
        self._unlink_tmp()
        # self.tasklist = {}
