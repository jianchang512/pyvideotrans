# -*- coding: utf-8 -*-
# primary ui
import copy
import datetime

import os
import time

from PySide6.QtCore import QThread
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import logger, homedir
from videotrans.translator import run as run_trans
from videotrans.recognition import run as run_recogn
from videotrans.tts import run as run_tts, text_to_speech
from videotrans.util.tools import runffmpeg, get_subtitle_from_srt, ms_to_time_string, set_process_box, speed_up_mp3


# 执行 ffmpeg 线程
class Worker(QThread):
    # update_ui = pyqtSignal(str)

    def __init__(self, cmd_list, func_name="logs", parent=None, no_decode=False):
        super(Worker, self).__init__(parent)
        self.cmd_list = cmd_list
        self.func_name = func_name
        self.no_decode = no_decode

    def run(self):
        set_process_box(f'starting ffmpeg...')
        for cmd in self.cmd_list:
            logger.info(f"[box]Will execute: ffmpeg {cmd=}")
            try:
                rs = runffmpeg(cmd, no_decode=self.no_decode, is_box=True)
                if not rs:
                    set_process_box(f'exec {cmd=} error', 'error')
            except Exception as e:
                logger.error("[bxo]FFmepg exec error:" + str(e))
                set_process_box("[bxo]FFmepg exec error:" + str(e))
                return f'[error]{str(e)}'
        set_process_box('ffmpeg succeed', "end", func_name=self.func_name)


# 执行语音识别
class WorkerWhisper(QThread):
    def __init__(self, *, audio_paths=None, model=None, language=None, func_name=None, model_type='faster', parent=None,out_path=None,is_cuda=False,split_type='split'):
        super(WorkerWhisper, self).__init__(parent)
        self.func_name = func_name
        self.audio_paths = audio_paths
        self.model = model
        self.model_type = model_type
        self.language = language
        self.out_path = out_path
        self.is_cuda=is_cuda
        self.split_type=split_type

    def run(self):
        set_process_box(f'start {self.model} ')
        errs = []
        length = len(self.audio_paths)
        time_dur = 1
        print('111')
        while len(self.audio_paths) > 0:
            try:
                config.box_recogn = 'ing'
                audio_path = self.audio_paths.pop(0)
                if not os.path.exists(audio_path):
                    if time_dur > 600:
                        errs.append(f'{audio_path} 不存在')
                        time_dur = 0
                        continue
                    self.audio_paths.append(audio_path)
                    time.sleep(1)
                    time_dur += 1
                    continue
                self.post_message("logs", f'{config.transobj["kaishitiquzimu"]}:{os.path.basename(audio_path)}')
                jindu = f'@@@@@@ {int((length - len(self.audio_paths)) * 49 / length)}%'
                self.post_message("replace_subtitle", jindu)
                srts = run_recogn(type=self.split_type, audio_file=audio_path, model_name=self.model,
                                  detect_language=self.language, set_p=False, cache_folder=config.TEMP_DIR,
                                  model_type=self.model_type,
                                  is_cuda=self.is_cuda)
                text = []
                for it in srts:
                    text.append(f'{it["line"]}\n{it["time"]}\n{it["text"].strip(".")}')
                text = "\n\n".join(text)
                with open(self.out_path + f"/{os.path.basename(audio_path)}.srt", 'w', encoding='utf-8') as f:
                    f.write(text)
                self.post_message("replace_subtitle", f'{text}{jindu}')
            except Exception as e:
                errs.append(f'失败，{str(e)}')
        self.post_message('allend', "" if len(errs) < 1 else "\n".join(errs))
        config.box_recogn = 'stop'

    def post_message(self, type, text):
        set_process_box(text, type, func_name=self.func_name)


# 合成
class WorkerTTS(QThread):
    def __init__(self, parent=None, *,
                 files=None,
                 role=None,
                 rate=None,
                 wavname=None,
                 tts_type=None,
                 func_name=None,
                 voice_autorate=False,
                 langcode=None,
                 tts_issrt=False):
        super(WorkerTTS, self).__init__(parent)
        self.all_text=[]
        self.func_name = func_name
        self.files = files
        self.role = role
        self.rate = rate
        self.wavname = wavname
        self.tts_type = tts_type
        self.tts_issrt = tts_issrt
        self.langcode=langcode
        self.voice_autorate = voice_autorate
        self.tmpdir = f'{homedir}/tmp'
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir, exist_ok=True)

    def run(self):
        config.box_tts = 'ing'
        if self.tts_issrt:
            self.all_text=[]
            if isinstance(self.files,str):
                self.all_text.append({"text":self.files.strip(),"file":"srt-voice"})
            else:
                for it in self.files:
                    content=""
                    try:
                        with open(it,'r',encoding='utf-8') as f:
                            content=f.read().strip()
                    except:
                        with open(it,'r',encoding='utf-8') as f:
                            content=f.read().strip()
                    finally:
                        if content:
                            self.all_text.append({"text":content,"file":os.path.basename(it)})

            try:
                errs,success=self.before_tts()
                config.box_tts = 'stop'
                if success==0:
                    self.post_message('error', f'全部失败了请打开输出目录中txt文件查看失败记录')
                elif errs>0:
                    self.post_message("end", f"失败{errs}个，成功{success}个，请查看输出目录中txt文件查看失败记录")
                else:
                    self.post_message("end", "Succeed")
            except Exception as e:
                config.box_tts = 'stop'
                self.post_message('error', f'srt create dubbing error:{str(e)}')
            return

        mp3 = self.wavname+".mp3"
        try:
            text_to_speech(
                text=self.files,
                role=self.role,
                rate=self.rate,
                filename=mp3,
                language=self.langcode,
                tts_type=self.tts_type,
                set_p=False
            )

            runffmpeg([
                '-y',
                '-i',
                f'{mp3}',
                "-c:a",
                "pcm_s16le",
                f'{self.wavname}.wav',
            ], no_decode=True, use_run=True)
            if os.path.exists(mp3):
                os.unlink(mp3)
        except Exception as e:
            config.box_tts = 'stop'
            self.post_message('error', f'srt create dubbing error:{str(e)}')
            return

        config.box_tts = 'stop'
        self.post_message("end", "Succeed")

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        length=len(self.all_text)
        errs=0
        for n,item in enumerate(self.all_text):
            queue_tts = []
            # 获取字幕
            percent=round(100*n/length,2)
            set_process_box(item['text'],'logs',func_name='hecheng_set')
            set_process_box(f'{percent+1}%','ing',func_name=self.func_name)
            subs = get_subtitle_from_srt(item["text"], is_file=False)
            rate = int(str(self.rate).replace('%', ''))
            if rate >= 0:
                rate = f"+{rate}%"
            else:
                rate = f"{rate}%"
            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            for it in subs:
                queue_tts.append({
                    "text": it['text'],
                    "role": self.role,
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "rate": rate,
                    "startraw": it['startraw'],
                    "endraw": it['endraw'],
                    "tts_type": self.tts_type,
                    "language":self.langcode,
                    "filename": f"{self.tmpdir}/tts-{it['start_time']}.mp3"})
            try:
                run_tts(queue_tts=copy.deepcopy(queue_tts), language=self.langcode,set_p=False)
                segments = []
                start_times = []
                # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
                # 偏移时间，用于每个 start_time 增减
                offset = 0
                # 将配音和字幕时间对其，修改字幕时间
                for (idx, it) in enumerate(queue_tts):
                    logger.info(f'\n\n{idx=},{it=}')
                    it['start_time'] += offset
                    it['end_time'] += offset
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                        start_times.append(it['start_time'])
                        segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                        queue_tts[idx] = it
                        continue
                    audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                    mp3len = len(audio_data)

                    # 原字幕发音时间段长度
                    wavlen = it['end_time'] - it['start_time']

                    if wavlen == 0 or mp3len==0:
                        queue_tts[idx] = it
                        continue
                    # 新配音大于原字幕里设定时长
                    diff = mp3len - wavlen
                    if diff > 0 and self.voice_autorate:
                        speed = mp3len / wavlen
                        if speed < 100:
                            # 新的长度
                            mp3len = mp3len / speed
                            diff = mp3len - wavlen
                            if diff < 0:
                                diff = 0
                            tmp_mp3 = os.path.join(config.TEMP_DIR, f'{it["filename"]}.mp3')
                            speed_up_mp3(filename=it['filename'], speed=speed, out=tmp_mp3)
                            audio_data = AudioSegment.from_file(tmp_mp3, format="mp3")
                            # 增加新的偏移
                            offset += diff
                    elif diff > 0:
                        offset += diff
                    it['end_time'] = it['start_time'] + mp3len
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    queue_tts[idx] = it
                    start_times.append(it['start_time'])
                    segments.append(audio_data)
                # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
                self.merge_audio_segments(segments, start_times,f'{self.wavname}-{item["file"]}.wav')

            except Exception as e:
                errs+=1
                # raise Exception(f'[error]tts error:{str(e)}')
                with open(f'{self.wavname}-error.txt','w',encoding='utf-8') as f:
                    f.write(f'srt文件 {item["file"]} 合成失败，原因为:{str(e)}\n\n原字幕内容为\n\n{item["text"]}')
            finally:
                percent=round(100*(n+1)/length,2)
                set_process_box(f'{percent}%','ing',func_name=self.func_name)
        return errs,length-errs

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts):
        queue_copy = copy.deepcopy(queue_tts)
        try:
            run_tts(queue_tts=queue_tts, language=self.langcode,set_p=False)
        except Exception as e:
            raise Exception(f'[error]tts error:{str(e)}')
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if len(queue_copy) < 1:
            raise Exception(f'出错了，{queue_copy=}')
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            for (idx, it) in enumerate(queue_copy):
                logger.info(f'\n\n{idx=},{it=}')
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                    queue_copy[idx] = it
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                mp3len = len(audio_data)

                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']

                if wavlen == 0:
                    queue_copy[idx] = it
                    continue
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                if diff > 0 and self.voice_autorate:
                    speed = mp3len / wavlen
                    if speed < 50:
                        # 新的长度
                        mp3len = mp3len / speed
                        diff = mp3len - wavlen
                        if diff < 0:
                            diff = 0
                        tmp_mp3 = os.path.join(config.TEMP_DIR, f'{it["filename"]}.mp3')
                        speed_up_mp3(filename=it['filename'], speed=speed, out=tmp_mp3)
                        audio_data = AudioSegment.from_file(tmp_mp3, format="mp3")
                        # 增加新的偏移
                        offset += diff
                elif diff > 0:
                    offset += diff
                it['end_time'] = it['start_time'] + mp3len
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times)
        except Exception as e:
            raise Exception(f"[error] exec_tts:" + str(e))
        return True

    # join all short audio to one ,eg name.mp4  name.mp4.wav
    def merge_audio_segments(self, segments, start_times,filename):
        merged_audio = AudioSegment.empty()
        # start is not 0
        if start_times[0] != 0:
            silence_duration = start_times[0]
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence

        # join
        for i in range(len(segments)):
            segment = segments[i]
            start_time = start_times[i]
            # add silence
            if i > 0:
                previous_end_time = start_times[i - 1] + len(segments[i - 1])
                silence_duration = start_time - previous_end_time
                # 前面一个和当前之间存在静音区间
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence

            merged_audio += segment
        # 创建配音后的文件
        merged_audio.export(filename, format="wav")

        return merged_audio

    def post_message(self, type, text=""):
        set_process_box(text, type, func_name=self.func_name)


class FanyiWorker(QThread):

    def __init__(self, type, target_language, text, issrt, parent=None):
        super(FanyiWorker, self).__init__(parent)
        self.type = type
        self.target_language = target_language
        self.text = text
        self.issrt = issrt
        self.srts = ""

    def run(self):
        # 开始翻译,从目标文件夹读取原始字幕
        set_process_box(f'start translate')
        config.box_trans = "ing"
        try:
            if not self.issrt:
                self.srts = run_trans(text_list=self.text, translate_type=self.type,
                                      target_language_name=self.target_language, set_p=False)
            else:
                try:
                    rawsrt = get_subtitle_from_srt(self.text, is_file=False)
                except Exception as e:
                    set_process_box(f"整理格式化原始字幕信息出错:" + str(e), 'error')
                    return ""
                srt = run_trans(translate_type=self.type, text_list=rawsrt, target_language_name=self.target_language,
                                set_p=False)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                self.srts = srts_tmp
        except Exception as e:
            set_process_box(str(e), "error", func_name="fanyi_end")
            return
        finally:
            config.box_trans = "stop"
        set_process_box(self.srts, "end", func_name="fanyi_end")
