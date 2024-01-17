# -*- coding: utf-8 -*-
# primary ui
import copy
import json
import os
import re

from PyQt5.QtCore import  pyqtSignal, QThread
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import logger, homedir
from videotrans.translator import deeplxtrans, deepltrans, tencenttrans, baidutrans, googletrans,  chatgpttrans, azuretrans, geminitrans
from videotrans.util.tools import transcribe_audio, text_to_speech, runffmpeg, \
    get_subtitle_from_srt, ms_to_time_string, speed_change, set_process_box


# 执行 ffmpeg 线程
class Worker(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, cmd_list, func_name="", parent=None, no_decode=False):
        super(Worker, self).__init__(parent)
        self.cmd_list = cmd_list
        self.func_name = func_name
        self.no_decode=no_decode

    def run(self):
        set_process_box(f'starting...')
        for cmd in self.cmd_list:
            logger.info(f"[box]Will execute: ffmpeg {cmd=}")
            try:
                rs=runffmpeg(cmd, no_decode=self.no_decode,is_box=True)
                if not rs:
                    set_process_box(f'exec {cmd=} error','error')
            except Exception as e:
                logger.error("[bxo]FFmepg exec error:" + str(e))
                set_process_box("[bxo]FFmepg exec error:" + str(e))
                self.post_message("error", "ffmpeg error")
                return f'[error]{str(e)}'
        self.post_message("end", "End\n")
        set_process_box(f'Ended','end')

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 执行语音识别
class WorkerWhisper(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, audio_path, model, language, func_name, parent=None):
        super(WorkerWhisper, self).__init__(parent)
        self.func_name = func_name
        self.audio_path = audio_path
        self.model = model
        self.language = language

    def run(self):
        set_process_box(f'start regcon {self.model}')
        try:
            text = transcribe_audio(self.audio_path, self.model, self.language)
            self.post_message("end", text)
        except Exception as e:
            self.post_message("error", str(e))


    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 合成
class WorkerTTS(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, parent=None, *,
                 text=None,
                 role=None,
                 rate=None,
                 filename=None,
                 tts_type=None,
                 func_name=None,
                 voice_autorate=False,
                 tts_issrt=False):
        super(WorkerTTS, self).__init__(parent)
        self.func_name = func_name
        self.text = text
        self.role = role
        self.rate = rate
        self.filename = filename
        self.tts_type = tts_type
        self.tts_issrt = tts_issrt
        self.voice_autorate = voice_autorate
        self.tmpdir = f'{homedir}/tmp'
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir, exist_ok=True)

    def run(self):
        set_process_box(f"start {self.tts_type=},{self.role=},{self.rate=}")

        if self.tts_issrt:
            try:
                q = self.before_tts()
            except Exception as e:
                self.post_message('error', f'before dubbing error:{str(e)}')
                return
            try:
                if not self.exec_tts(q):
                    self.post_message('error', f'srt create dubbing error:view logs')
                    return
            except Exception as e:
                self.post_message('error', f'srt create dubbing error:{str(e)}')
                return
        else:
            mp3 = self.filename.replace('.wav', '.mp3')
            if not text_to_speech(
                text=self.text,
                role=self.role,
                rate=self.rate,
                filename=mp3,
                tts_type=self.tts_type
            ):
                self.post_message('error', f'srt create dubbing error:view logs')
                return

            runffmpeg([
                '-y',
                '-i',
                f'{mp3}',
                "-c:a",
                "pcm_s16le",
                f'{self.filename}',
            ], no_decode=True,is_box=True)
            os.unlink(mp3)
        self.post_message("end", "Ended")

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        queue_tts = []
        # 获取字幕
        subs = get_subtitle_from_srt(self.text, is_file=False)
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
                "filename": f"{self.tmpdir}/tts-{it['start_time']}.mp3"})
        return queue_tts

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts):
        queue_copy = copy.deepcopy(queue_tts)
        # 需要并行的数量3
        while len(queue_tts) > 0:
            try:
                q=queue_tts.pop(0)
                if not text_to_speech(text=q['text'],role=q['role'], rate=q['rate'], filename=q["filename"],
                    tts_type=self.tts_type):
                    return False
            except Exception as e:
                self.post_message('end', f'[error]tts error:{str(e)}')
                return False
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if len(queue_copy) < 1:
            return self.post_message('error', f'出错了，{queue_copy=}')
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            srtmeta = []
            for (idx, it) in enumerate(queue_copy):
                srtmeta_item = {
                    'dubbing_time': -1,
                    'source_time': -1,
                    'speed_up': -1,
                }
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
                # 新配音时长
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_up'] = 0
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                if diff > 0 and self.voice_autorate:
                    speed = mp3len / wavlen
                    speed = 1.8 if speed > 1.8 else speed
                    srtmeta_item['speed_up'] = speed
                    # 新的长度
                    mp3len = mp3len / speed
                    diff = mp3len - wavlen
                    if diff < 0:
                        diff = 0
                    # 音频加速 最大加速2倍
                    audio_data = speed_change(audio_data, speed)
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
                srtmeta.append(srtmeta_item)
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times)
        except Exception as e:
            self.post_message('error', f"[error] exec_tts :" + str(e))
            return False
        return True

    # join all short audio to one ,eg name.mp4  name.mp4.wav
    def merge_audio_segments(self, segments, start_times):
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
        merged_audio.export(self.filename, format="wav")

        return merged_audio

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))

class FanyiWorker(QThread):
    ui = pyqtSignal(str)

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
        if not self.issrt:
            if self.type == 'chatGPT':
                self.srts = chatgpttrans(self.text, self.target_language, set_p=False)
            elif self.type == 'Azure':
                self.srts = azuretrans(self.text, self.target_language, set_p=False)
            elif self.type == 'Gemini':
                self.srts = geminitrans(self.text, self.target_language, set_p=False)
            elif self.type == 'google':
                self.srts = googletrans(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'baidu':
                self.srts = baidutrans(self.text, 'auto', self.target_language, set_p=False)

            elif self.type == 'tencent':
                self.srts = tencenttrans(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'DeepL':
                self.srts = deepltrans(self.text, self.target_language, set_p=False)
            elif self.type == 'DeepLX':
                self.srts = deeplxtrans(self.text, self.target_language, set_p=False)
        else:
            try:
                rawsrt = get_subtitle_from_srt(self.text, is_file=False)
            except Exception as e:
                set_process_box(f"整理格式化原始字幕信息出错:" + str(e), 'error')
                return ""
            if self.type in ['chatGPT', 'Azure', 'Gemini']:
                if self.type == 'chatGPT':
                    srt = chatgpttrans(rawsrt, self.target_language, set_p=False)
                elif self.type == 'Azure':
                    srt = azuretrans(rawsrt, self.target_language, set_p=False)
                elif self.type == 'Gemini':
                    srt = geminitrans(rawsrt, self.target_language, set_p=False)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                self.srts = srts_tmp
            else:
                split_size = config.settings['trans_thread']
                srt_lists = [rawsrt[i:i + split_size] for i in range(0, len(rawsrt), split_size)]
                for (index, item) in enumerate(srt_lists):
                    wait_text = []
                    for (i, it) in enumerate(item):
                        wait_text.append(it['text'].strip().replace("\n", '.'))
                    wait_text = "\n".join(wait_text)
                    # 翻译
                    new_text = ""
                    if self.type == 'google':
                        new_text = googletrans(wait_text,
                                               'auto',
                                               self.target_language, set_p=False)
                    elif self.type == 'baidu':
                        new_text = baidutrans(wait_text, 'auto', self.target_language, set_p=False)
                    elif self.type == 'tencent':
                        new_text = tencenttrans(wait_text, 'auto', self.target_language, set_p=False)
                    elif self.type == 'DeepL':
                        new_text = deepltrans(wait_text, self.target_language, set_p=False)
                    elif self.type == 'DeepLX':
                        new_text = deeplxtrans(wait_text, self.target_language, set_p=False)
                    trans_text = re.sub(r'&#\d+;', '', new_text).replace('&#39;', "'").split("\n")
                    srt_str = ""
                    for (i, it) in enumerate(item):
                        if i <= len(trans_text) - 1:
                            srt_str += f"{it['line']}\n{it['time']}\n{trans_text[i]}\n\n"
                        else:
                            srt_str += f"{it['line']}\n{it['time']}\n{item['text']}\n\n"
                    self.srts +=srt_str

                # 其他翻译，逐行翻译
                for (i, it) in enumerate(rawsrt):
                    new_text = it['text']
                    if self.type == 'google':
                        new_text = googletrans(it['text'],
                                               'auto',
                                               self.target_language, set_p=False)
                    elif self.type == 'baidu':
                        new_text = baidutrans(it['text'], 'auto', self.target_language, set_p=False)
                    elif self.type == 'tencent':
                        new_text = tencenttrans(it['text'], 'auto', self.target_language, set_p=False)
                    elif self.type == 'DeepL':
                        new_text = deepltrans(it['text'], self.target_language, set_p=False)
                    elif self.type == 'DeepLX':
                        new_text = deeplxtrans(it['text'], self.target_language, set_p=False)
                    new_text = re.sub(r'&#\d+;', '', new_text.replace('&#39;', "'"))
                    # 更新字幕区域
                    self.srts += f"{it['line']}\n{it['time']}\n{new_text}\n\n"


        self.ui.emit(json.dumps({"func_name": "fanyi_end", "type": "end", "text": self.srts}))

