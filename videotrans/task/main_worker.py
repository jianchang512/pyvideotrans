# -*- coding: utf-8 -*-
import hashlib
import os
import time

from PyQt5.QtCore import QThread
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import transobj
from videotrans.task.trans_create import TransCreate
from videotrans.util.tools import set_process, delete_temp, get_subtitle_from_srt, text_to_speech, \
    speed_change, pygameaudio, get_line_role


class Worker(QThread):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.video=None

    def run(self) -> None:
        task_nums=len(config.queue_task)
        num=0
        # html=[]
        # stylecss="""padding:5px;margin:5px;color:#00a67d;"""
        while len(config.queue_task)>0:
            num+=1
            it=config.queue_task.pop(0)
            set_process(f"Starting")
            set_process(f"Processing {num}/{task_nums}",'statusbar')
            self.video=TransCreate(it)
            res=self.video.run()
            if res is True:
                set_process(f"{self.video.target_dir}",'succeed')
                config.params['line_roles']={}
            elif res is False:
                return
        # 全部完成
        set_process( "",'end')
        time.sleep(10)
        delete_temp(None)

class Shiting(QThread):
    def __init__(self, obj,parent=None):
        super().__init__(parent=parent)
        self.obj=obj
        self.stop=False
    def run(self):
        # 获取字幕
        try:
            subs = get_subtitle_from_srt(self.obj['sub_name'])
        except Exception as e:
            set_process(f'{transobj["geshihuazimuchucuo"]}:{str(e)}')
            return False
        rate = int(str(config.params["voice_rate"]).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        # 取出设置的每行角色
        line_roles= get_line_role(config.params["line_roles"]) if "line_roles" in config.params else None
        for it in subs:
            if config.task_countdown<=0 or self.stop:
                return
            if config.current_status != 'ing':
                set_process(transobj['tingzhile'], 'stop')
                return True
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role=config.params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role=line_roles[f'{it["line"]}']
            filename=f'{voice_role}-{config.params["voice_rate"]}-{config.params["voice_autorate"]}-{it["text"]}'
            md5_hash = hashlib.md5()
            md5_hash.update(f"{filename}".encode('utf-8'))
            filename = self.obj['cache_folder']+"/"+md5_hash.hexdigest()+".mp3"
            text_to_speech(text=it['text'],
                 role=voice_role,
                 rate= rate,
                 filename=filename,
                 tts_type= config.params['tts_type']
            )
            audio_data = AudioSegment.from_file(filename, format="mp3")
            mp3len = len(audio_data)

            wavlen = it['end_time'] - it['start_time']
            # 新配音大于原字幕里设定时长
            diff = mp3len - wavlen
            if diff > 0 and config.params["voice_autorate"]:
                speed = mp3len / wavlen
                speed = 1.8 if speed > 1.8 else round(speed, 2)
                set_process(f"dubbing speed {speed} ")
                # 音频加速 最大加速2倍
                audio_data = speed_change(audio_data, speed)
            tmp=time.time()
            audio_data.export(f"{filename}-{tmp}.wav",format="wav")
            set_process(f'Listening:{it["text"]}')
            pygameaudio(f"{filename}-{tmp}.wav")
            try:
                os.unlink(f"{filename}-{tmp}.wav")
            except:
                pass