import copy
import datetime
import hashlib
import json
import os
import re
import shutil
import textwrap
import threading
import time
from datetime import timedelta

import speech_recognition as sr
#import whisper
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.configure.config import transobj, logger, homedir
from videotrans.translator import chatgpttrans, googletrans, baidutrans, tencenttrans, baidutrans_spider, deepltrans, deeplxtrans,azuretrans,geminitrans
from videotrans.util.tools import runffmpeg, set_process, delete_files, match_target_amplitude, show_popup, \
    shorten_voice, \
    ms_to_time_string, get_subtitle_from_srt, get_lastjpg_fromvideo, get_video_fps, get_video_resolution, \
    is_novoice_mp4, cut_from_video, get_video_duration, text_to_speech, speed_change, delete_temp, get_line_role

import torch
device= "cuda" if config.params['cuda'] else "cpu"

class TransCreate():

    def __init__(self, obj):
        # 一条待处理的完整信息
        # config.params = config.params
        # config.params.update(obj)
        self.step = 'prepare'
        # 仅提取字幕，不嵌入字幕，不配音，仅用于提取字幕
        # 【从视频提取出字幕文件】
        self.only_srt = config.params['subtitle_type'] < 1 and config.params['voice_role'] in ['No', 'no', '-']
        # 原始视频
        self.source_mp4 = obj['source_mp4'].replace('\\', '/') if 'source_mp4' in obj else ""

        # 没有视频，是根据字幕生成配音
        if not self.source_mp4:
            self.noextname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.target_dir = f"{homedir}/only_dubbing"
        else:
            # 去掉扩展名的视频名，做标识
            self.noextname = os.path.splitext(os.path.basename(self.source_mp4))[0]
            if not config.params['target_dir']:
                self.target_dir = (os.path.dirname(self.source_mp4) + "/_video_out").replace('\\', '/')
            else:
                self.target_dir = config.params['target_dir'].replace('\\', '/')
        # 全局目标，用于前台打开
        self.target_dir=self.target_dir.replace('//', '/')
        config.params['target_dir']=self.target_dir
        #真实具体到每个文件目标
        self.target_dir += f"/{self.noextname}"
        set_process(self.target_dir,'set_target_dir')

        # 临时文件夹
        self.cache_folder = f"{config.rootdir}/tmp/{self.noextname}"

        # 分离出的原始音频文件
        self.source_wav = f"{self.cache_folder}/{self.noextname}.wav"
        # 配音后的tts音频
        self.tts_wav = f"{self.cache_folder}/tts-{self.noextname}.wav"
        # 翻译后的字幕文件-存于缓存
        self.sub_name = f"{self.cache_folder}/{self.noextname}.srt"
        self.source_mp4_length = -1

        print(f'noextname={self.noextname},target_dir={self.target_dir}')

        # 创建文件夹
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder, exist_ok=True)
        # 源语言字幕和目标语言字幕
        self.novoice_mp4 = f"{self.target_dir}/novoice.mp4"
        self.targetdir_source_sub = f"{self.target_dir}/{config.params['source_language']}.srt"
        self.targetdir_target_sub = f"{self.target_dir}/{config.params['target_language']}.srt"
        # 原wav和目标音频
        self.targetdir_source_wav = f"{self.target_dir}/{config.params['source_language']}.wav"
        self.targetdir_target_wav = f"{self.target_dir}/{config.params['target_language']}.wav"
        self.targetdir_mp4 = f"{self.target_dir}/{self.noextname}.mp4"
        # 如果存在字幕，则直接生成
        if "subtitles" in obj and obj['subtitles']:
            # 如果原语言和目标语言相同，或不存在视频，则不翻译
            with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
                f.write(obj['subtitles'].strip())

    # 启动执行入口
    def run(self):
        # 存在视频并且不是仅提取字幕，则分离
        if self.source_mp4 and os.path.exists(self.source_mp4):
            set_process(f'audio and video split')
            if not self.split_wav_novicemp4():
                set_process("split error", 'error')
                return False

        #####识别阶段 存在视频，且存在原语言字幕，如果界面无字幕，则填充
        if self.source_mp4 and os.path.exists(self.targetdir_source_sub):
            # 通知前端替换字幕
            with open(self.targetdir_source_sub, 'r', encoding="utf-8") as f:
                set_process(f.read().strip(), 'replace_subtitle')
        # 如果存在视频，且没有已识别过的，则需要识别
        if self.source_mp4 and not os.path.exists(self.targetdir_source_sub) and not os.path.exists(
                self.targetdir_target_sub):
            set_process(f'start speech to text')
            if not self.recongn():
                set_process("recognition error", 'error')
                return False

        ##### 翻译阶段
        # 如果存在视频，并且存在目标语言字幕，则前台直接使用该字幕替换
        if self.source_mp4 and os.path.exists(self.targetdir_target_sub):
            # 通知前端替换字幕
            with open(self.targetdir_target_sub, 'r', encoding="utf-8") as f:
                set_process(f.read().strip(), 'replace_subtitle')

        # 是否需要翻译，如果存在视频，并且存在目标语言，并且原语言和目标语言不同，并且没有已翻译过的，则需要翻译
        self.step = 'translate_before'
        if self.source_mp4 \
                and config.params['target_language'] not in ['No', 'no', '-'] \
                and config.params['target_language'] != config.params['source_language'] \
                and not os.path.exists(self.targetdir_target_sub):
            # 等待编辑原字幕后翻译
            set_process(transobj["xiugaiyuanyuyan"], 'edit_subtitle')
            config.task_countdown = 60
            while config.task_countdown > 0:
                if config.task_countdown <= 60 and config.task_countdown >= 0:
                    set_process(f"{config.task_countdown} {transobj['jimiaohoufanyi']}", 'show_djs')
                time.sleep(1)
                config.task_countdown -= 1
            set_process('', 'timeout_djs')
            time.sleep(2)
            if not self.trans():
                set_process("translate error.", 'error')
                return False
            set_process('Translate end')
        self.step = 'translate_end'

        # 如果仅仅需要提取字幕（不配音、不嵌入字幕），到此返回
        # 【从视频提取出字幕文件】
        # 选择视频文件，选择视频源语言，如果选择目标语言，则会输出翻译后的字幕文件，其他无需选择，开始执行
        if self.only_srt:
            set_process(f"Ended")
            # 检测是否还有
            return True

        # 如果存在目标语言字幕，并且存在 配音角色，则需要配音
        self.step = "dubbing_before"
        if config.params['voice_role'] not in ['No', 'no', '-'] \
                and os.path.exists(self.targetdir_target_sub) \
                and not os.path.exists(self.targetdir_target_wav):
            set_process(transobj["xiugaipeiyinzimu"], "edit_subtitle")
            config.task_countdown = 60
            while config.task_countdown > 0:
                if config.current_status != 'ing':
                    set_process(transobj["tingzhile"], 'stop')
                    return False

                # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                time.sleep(1)
                # 倒计时中
                config.task_countdown -= 1
                if config.task_countdown <= 60 and config.task_countdown >= 0:
                    set_process(f"{config.task_countdown}{transobj['zidonghebingmiaohou']}", 'show_djs')
            # set_process(f"<br>开始配音操作:{config.params['tts_type']},{config.params['voice_role']}")
            set_process('', 'timeout_djs')
            time.sleep(3)
            self.step = 'dubbing_ing'
            try:
                # 包含 音频自动加速和视频自动降速，创建 tts.wav
                res = self.before_tts()
            except Exception as e:
                set_process("[error]" + str(e), "error")
                return False
            try:
                if isinstance(res, tuple):
                    self.exec_tts(res[0], res[1])
            except Exception as e:
                set_process("[error]" + str(e), "error")
                delete_temp(self.noextname)
                return False
            set_process('Dubbing ended')

        self.step = 'dubbing_end'
        # 如果不需要合成，比如仅配音
        if not self.source_mp4:
            set_process('Ended')
            return True

        # 最后一步合成
        self.step = 'compos_before'
        try:
            set_process(f"Start last step")
            if self.compos_video():
                time.sleep(1)
        except Exception as e:
            set_process(f"[error]:last step error " + str(e), "error")
            delete_temp(self.noextname)
            return False
        self.step = 'compos_end'
        return True

    # 分离音频 和 novoice.mp4
    def split_wav_novicemp4(self):
        '''
            from spleeter.separator import Separator
            separator = Separator('spleeter:2stems', multiprocess=False)
            separator.separate_to_file(a_name, destination=dirname, filename_format="{filename}{instrument}.{codec}")
            a_name = f"{dirname}/{noextname}vocals.wav"
        '''
        # 单独提前分离出 novice.mp4
        # 要么需要嵌入字幕 要么需要配音，才需要分离
        if self.source_mp4 and not os.path.exists(self.novoice_mp4):
            ffmpegars = [
                "-y",
                "-i",
                f'{self.source_mp4}',
                "-an",
                "-c:v", 
                "h264_nvenc" if config.params["cuda"] else "copy",
                f'{self.novoice_mp4}'
            ]
            threading.Thread(target=runffmpeg, args=(ffmpegars,), kwargs={"noextname": self.noextname}).start()
        else:
            config.queue_novice[self.noextname]='end'
        # 如果原语言和目标语言一样，则不分离
        if config.params['source_language'] == config.params['target_language']:
            return True
        
        # 如果不存在音频，则分离出音频
        if os.path.exists(self.source_mp4) and not os.path.exists(self.targetdir_source_wav):
            # set_process(f"{self.noextname} 分析视频数据", "logs")
            try:
                if not runffmpeg([
                    "-y",
                    "-i",
                    f'{self.source_mp4}',
                    "-ac",
                    "1",
                    f'{self.targetdir_source_wav}'
                ]):
                    set_process(f'[error]', 'error')
                    return False
            except Exception as e:
                set_process(f'{str(e)}', 'error')
                return False
        return True

    # 识别出字幕
    def recongn(self):
        while not os.path.exists(self.targetdir_source_wav):
            set_process(transobj["running"])
            time.sleep(1)
        try:
            # 识别为字幕
            if config.params['whisper_type'] == 'all':
                return self.recognition_all()
            else:
                return self.recognition_split()
            # 识别出的源语言字幕
        except Exception as e:
            set_process(f"error:" + str(e), 'error')
            set_process(transobj["tingzhile"], 'stop')
        return False

    # 翻译字幕
    def trans(self):
        try:
            self.srt_translation_srt()
            return True
        except Exception as e:
            set_process(f"translate error:" + str(e), 'error')
            set_process(transobj["tingzhile"], 'stop')
        return False

    # split audio by silence
    def shorten_voice(self, normalized_sound):
        normalized_sound = match_target_amplitude(normalized_sound, -20.0)
        max_interval = 10000
        buffer = 500
        nonsilent_data = []
        audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.params['voice_silence']),
                                        silence_thresh=-20 - 25)
        # print(audio_chunks)
        for i, chunk in enumerate(audio_chunks):
            start_time, end_time = chunk
            n = 0
            while end_time - start_time >= max_interval:
                n += 1
                # new_end = start_time + max_interval+buffer
                new_end = start_time + max_interval + buffer
                new_start = start_time
                nonsilent_data.append((new_start, new_end, True))
                start_time += max_interval
            nonsilent_data.append((start_time, end_time, False))
        return nonsilent_data

    # join all short audio to one ,eg name.mp4  name.mp4.wav
    def merge_audio_segments(self, segments, start_times, total_duration):
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
        if total_duration > 0 and (len(merged_audio) < total_duration):
            # 末尾补静音
            silence = AudioSegment.silent(duration=total_duration - len(merged_audio))
            merged_audio += silence
        # 如果新长度大于原时长，则末尾截断
        if total_duration > 0 and (len(merged_audio) > total_duration):
            # 截断前先保存原完整文件
            merged_audio.export(f'{self.target_dir}/{config.params["target_language"]}-nocut.wav', format="wav")
            merged_audio = merged_audio[:total_duration]
        # 创建配音后的文件
        merged_audio.export(f"{self.targetdir_target_wav}", format="wav")
        return merged_audio

    # noextname 是去掉 后缀mp4的视频文件名字
    # 所有临时文件保存在 /tmp/noextname文件夹下
    # 分批次读取
    def recognition_split(self):
        set_process("预先分割数据进行语音识别")
        if config.current_status == 'stop':
            return False
        tmp_path = f'{self.cache_folder}/##{self.noextname}_tmp'
        if not os.path.isdir(tmp_path):
            try:
                os.makedirs(tmp_path, 0o777, exist_ok=True)
            except:
                show_popup(transobj["anerror"], transobj["createdirerror"])

        normalized_sound = AudioSegment.from_wav(self.targetdir_source_wav)  # -20.0
        nonslient_file = f'{tmp_path}/detected_voice.json'
        if os.path.exists(nonslient_file) and os.path.getsize(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            if config.current_status == 'stop':
                return False
            nonsilent_data = shorten_voice(normalized_sound)
            set_process(f"对音频文件按静音片段分割处理", 'logs')
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)
        #r = sr.Recognizer()
        r = WhisperModel(config.params['whisper_model'], device=device,  compute_type="int8" if device=='cpu' else "int8_float16", download_root=config.rootdir + "/models")
        raw_subtitles = []
        offset = 0
        language="zh" if config.params['detect_language'] == "zh-cn" or config.params['detect_language'] == "zh-tw" else config.params['detect_language']
        for i, duration in enumerate(nonsilent_data):
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            start_time, end_time, buffered = duration
            start_time += offset
            end_time += offset
            if start_time == end_time:
                end_time += 200
                # 如果加了200后，和下一个开始重合，则偏移
                if (i < len(nonsilent_data) - 1) and nonsilent_data[i + 1][0] < end_time:
                    offset += 200
            time_covered = start_time / len(normalized_sound) * 100
            # 进度
            set_process(f"音频处理进度{time_covered:.1f}%")
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            add_vol = 0
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format="wav")

            if config.current_status == 'stop':
                raise Exception("You stop it.")
            text=""
            try:               
                #print(chunk_filename)
                segments,_ = r.transcribe(chunk_filename, 
                            beam_size=5,  
                            language=language)
                #print(segments)
                for t in segments:
                    text+=t.text+" "
                    print(f'{t.text}')
            except sr.UnknownValueError as e:
                set_process("[error]:语音识别出错了:" + str(e))
                continue
            except Exception as e:
                set_process("[error]:语音识别出错了:" + str(e))
                continue
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            text = f"{text.capitalize()}. ".replace('&#39;', "'")
            text = re.sub(r'&#\d+;', '', text).strip()
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue
            
            start = timedelta(milliseconds=start_time)

            stmp = str(start).split('.')
            if len(stmp) == 2:
                start = f'{stmp[0]},{int(int(stmp[-1]) / 1000)}'
            end = timedelta(milliseconds=end_time)
            etmp = str(end).split('.')
            if len(etmp) == 2:
                end = f'{etmp[0]},{int(int(etmp[-1]) / 1000)}'
            line=len(raw_subtitles) + 1
            set_process(f"{line}\n{start} --> {end}\n{text}\n\n",'subtitle')
            raw_subtitles.append({"line": line, "time": f"{start} --> {end}", "text": text})
        set_process(f"字幕识别完成，共{len(raw_subtitles)}条字幕", 'logs')
        # 写入原语言字幕到目标文件夹
        self.save_srt_target(raw_subtitles, self.targetdir_source_sub)
        return True

    # 整体识别，全部传给模型
    def recognition_all(self):
        model = config.params['whisper_model']
        language = "zh" if config.params['detect_language'] in ["zh-cn", "zh-tw"] else config.params['detect_language']
        set_process(f"Model:{model} ")
        try:
            model = WhisperModel(config.params['whisper_model'], device=device, compute_type="int8" if device=='cpu' else "int8_float16", download_root=config.rootdir + "/models")
            segments,_ = model.transcribe(self.targetdir_source_wav, 
                            beam_size=5,  
                            vad_filter=True,
                            vad_parameters=dict(min_silence_duration_ms=config.params['voice_silence']),
                            language=language)
            # 保留原始语言的字幕
            raw_subtitles = []
            offset = 0
            sidx=-1
            for segment in segments:
                sidx+=1
                if config.current_status == 'stop' or config.current_status == 'end':
                    return
                start = int(segment.start * 1000) + offset
                end = int(segment.end * 1000) + offset
                if start == end:
                    end += 200
                    if sidx < len(segments) - 1 and (int(segments[sidx + 1].start * 1000) < end):
                        offset += 200
                startTime = ms_to_time_string(ms=start)
                endTime = ms_to_time_string(ms=end)
                text = segment.text.strip().replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)

                # 无有效字符
                if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(
                        text) <= 1:
                    continue
                # 原语言字幕
                raw_subtitles.append(
                    {"line": len(raw_subtitles) + 1, "time": f"{startTime} --> {endTime}", "text": text})
            set_process(f"srt:{len(raw_subtitles)}", 'logs')
            # 写入翻译前的原语言字幕到目标文件夹
            self.save_srt_target(raw_subtitles, self.targetdir_source_sub)

        except Exception as e:
            set_process(f"{model} error:{str(e)}", 'error')
            return False
        return True

    # 单独处理翻译,完整字幕由 src翻译为 target
    def srt_translation_srt(self):
        # 如果不存在原字幕，则跳过，比如使用已有字幕，无需翻译时
        if not os.path.exists(self.targetdir_source_sub):
            return True
        # 开始翻译,从目标文件夹读取原始字幕
        try:
            rawsrt = get_subtitle_from_srt(self.targetdir_source_sub, is_file=True)
        except Exception as e:
            set_process(f"subtitle srt error:" + str(e), 'error')
            return False
        if config.params['translate_type'] == 'chatGPT':
            set_process(f"waitting chatGPT", 'logs')
            try:
                rawsrt = chatgpttrans(rawsrt,config.params['target_language_chatgpt'])
            except Exception as e:
                set_process(f'ChatGPT error:{str(e)}', 'error')
                return False
        elif config.params['translate_type'] == 'Azure':
            set_process(f"waitting Azure ", 'logs')
            try:
                rawsrt = azuretrans(rawsrt,config.params['target_language_azure'])
            except Exception as e:
                set_process(f'Azure error:{str(e)}', 'error')
                return False
        elif config.params['translate_type']=='Gemini':
            set_process(f"waitting Gemini", 'logs')
            try:
                rawsrt = geminitrans(rawsrt,config.params['target_language_gemini'])
            except Exception as e:
                set_process(f'Gemini:{str(e)}', 'error')
                return False
        else:
            # 其他翻译，逐行翻译
            for (i, it) in enumerate(rawsrt):
                if config.current_status != 'ing':
                    return
                new_text = it['text']
                if config.params['translate_type'] == 'google':
                    new_text = googletrans(it['text'],
                                           config.params['source_language'],
                                           config.params['target_language'])
                elif config.params['translate_type'] == 'baidu':
                    new_text = baidutrans(it['text'], 'auto', config.params['target_language_baidu'])
                elif config.params['translate_type'] == 'tencent':
                    new_text = tencenttrans(it['text'], 'auto', config.params['target_language_tencent'])
                elif config.params['translate_type'] == 'baidu(noKey)':
                    new_text = baidutrans_spider(it['text'], 'auto', config.params['target_language_baidu'])
                elif config.params['translate_type'] == 'DeepL':
                    new_text = deepltrans(it['text'], config.params['target_language_deepl'])
                elif config.params['translate_type'] == 'DeepLX':
                    new_text = deeplxtrans(it['text'], config.params['target_language_deepl'])
                new_text = new_text.replace('&#39;', "'")
                new_text = re.sub(r'&#\d+;', '', new_text)
                # 更新字幕区域
                set_process(f"{it['line']}\n{it['time']}\n{new_text}\n\n", "subtitle")
                it['text'] = new_text
                rawsrt[i] = it
        set_process(f"Translation end")
        # 保存到 翻译后的 字幕 到tmp缓存
        # self.save_srt_tmp(rawsrt)
        # 保存翻译后的字幕到目标文件夹
        self.save_srt_target(rawsrt, self.targetdir_target_sub)
        return True

    # 保存字幕到 tmp 临时文件
    # srt是字幕的dict list
    def save_srt_tmp(self, srt):
        # 是字幕列表形式，重新组装
        if isinstance(srt, list):
            txt = ""
            for it in srt:
                txt += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(self.sub_name, 'w', encoding="utf-8") as f:
                f.write(txt.strip())
        return True

    # 保存字幕文件 到目标文件夹
    def save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        if isinstance(srtstr, list):
            txt = ""
            for it in srtstr:
                txt += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(file, 'w', encoding="utf-8") as f:
                f.write(txt.strip())
                set_process(txt.strip(),'replace_subtitle')
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        if os.path.exists(self.targetdir_source_wav):
            normalized_sound = AudioSegment.from_wav(self.targetdir_source_wav)
            total_length = len(normalized_sound) / 1000
        else:
            total_length=0

        # 整合一个队列到 exec_tts 执行
        if config.params['voice_role'] not in ['No', 'no', '-']:
            queue_tts = []
            # 获取字幕
            try:
                subs = get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                set_process(f'srt error:{str(e)}', 'error')
                return False
            rate = int(str(config.params['voice_rate']).replace('%', ''))
            if rate >= 0:
                rate = f"+{rate}%"
            else:
                rate = f"{rate}%"
                # 取出设置的每行角色
            line_roles = get_line_role(config.params["line_roles"]) if "line_roles" in config.params else None
            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            for it in subs:
                if config.current_status != 'ing':
                    set_process(transobj['tingzhile'], 'stop')
                    return True
                    # 判断是否存在单独设置的行角色，如果不存在则使用全局
                voice_role = config.params['voice_role']
                if line_roles and f'{it["line"]}' in line_roles:
                    voice_role = line_roles[f'{it["line"]}']
                filename = f'{voice_role}-{config.params["voice_rate"]}-{config.params["voice_autorate"]}-{it["text"]}'
                md5_hash = hashlib.md5()
                md5_hash.update(f"{filename}".encode('utf-8'))
                filename = self.cache_folder + "/" + md5_hash.hexdigest() + ".mp3"
                queue_tts.append({
                    "text": it['text'],
                    "role": voice_role,
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "rate": rate,
                    "startraw": it['startraw'],
                    "endraw": it['endraw'],
                    "filename": filename})
            return (queue_tts, total_length)
        return True

    # 延长 novoice.mp4  duration_ms 毫秒
    def novoicemp4_add_time(self, duration_ms):
        while not is_novoice_mp4(self.novoice_mp4,self.noextname):
            time.sleep(1)
        # 截取最后一帧图片
        img = f'{self.cache_folder}/last.jpg'
        # 截取的图片组成 时长 duration_ms的视频
        last_clip = f'{self.cache_folder}/last_clip.mp4'
        # 取出最后一帧创建图片
        if not get_lastjpg_fromvideo(self.novoice_mp4, img):
            return False
        # 取出帧率
        fps = get_video_fps(self.novoice_mp4)
        if not fps:
            return False
        # 取出分辨率
        scale = get_video_resolution(self.novoice_mp4)
        if not scale:
            return False
        # 创建 ms 格式
        totime = ms_to_time_string(ms=duration_ms).replace(',', '.')
        # 创建 totime 时长的视频
        rs = runffmpeg([
            '-loop', '1', '-i', f'{img}', '-vf', f'fps={fps},scale={scale[0]}:{scale[1]}', '-c:v', "libx264",
            '-crf', '0', '-to', f'{totime}', '-pix_fmt', f'yuv420p', '-y', f'{last_clip}'])
        if not rs:
            return False
        # 开始将 novoice_mp4 和 last_clip 合并
        shutil.copy2(self.novoice_mp4, f'{self.novoice_mp4}.raw.mp4')
        res=runffmpeg(
            ['-y', '-i', f'{self.novoice_mp4}.raw.mp4', '-i', f'{last_clip}', f'-filter_complex',
             '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264", '-crf', '0', '-an',
             f'{self.novoice_mp4}'])
        try:
            os.unlink(f'{self.novoice_mp4}.raw.mp4')
        except:
            pass
        return res

    # 视频自动降速处理
    # 视频自动降速处理
    def video_autorate_process(self, queue_params, source_mp4_total_length):
        while not is_novoice_mp4(self.novoice_mp4,self.noextname):
            time.sleep(1)
        segments = []
        start_times = []
        # 预先创建好的
        # 处理过程中不断变化的 novoice_mp4
        novoice_mp4_tmp = f"{self.cache_folder}/novoice_tmp.mp4"

        queue_copy = copy.deepcopy(queue_params)
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            return False
        total_length = 0
        try:
            # 增加的时间，用于 修改字幕里的开始显示时间和结束时间
            offset = 0
            last_index = len(queue_params) - 1
            # set_process(f"原mp4长度={source_mp4_total_length=}")
            line_num = 0
            cut_clip = 0
            srtmeta = []
            for (idx, it) in enumerate(queue_params):
                if config.current_status != 'ing':
                    return False
                # 原发音时间段长度
                wavlen = it['end_time'] - it['start_time']
                if wavlen == 0:
                    # 舍弃
                    continue
                line_num += 1
                srtmeta_item = {
                    'dubbing_time': -1,
                    'source_time': -1,
                    'speed_down': -1,
                    "text": it['text'],
                    "line": line_num
                }
                # 该片段配音失败
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    total_length += wavlen
                    it['start_time'] += offset
                    it['end_time'] = it['start_time'] + wavlen
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])

                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=wavlen))
                    srtmeta.append(srtmeta_item)
                    queue_params[idx] = it
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")

                # 新发音长度
                mp3len = len(audio_data)
                if mp3len == 0:
                    srtmeta.append(srtmeta_item)
                    continue
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_down'] = 0

                # 先判断，如果 新时长大于旧时长，需要处理，这个最好需要加到 offset
                diff = mp3len - wavlen
                # 新时长大于旧时长，视频需要降速播放
                if diff > 0:
                    # 总时长 毫秒
                    total_length += mp3len
                    # 调整视频，新时长/旧时长
                    pts = round(mp3len / wavlen, 2)
                    if pts != 0:
                        srtmeta_item['speed_down'] = round(1 / pts, 2)
                    # 第一个命令
                    startmp4 = f"{self.cache_folder}/novice-{idx}-start.mp4"
                    clipmp4 = f"{self.cache_folder}/novice-{idx}-clip.mp4"
                    endmp4 = f"{self.cache_folder}/novice-{idx}-end.mp4"
                    # 开始时间要加上 offset
                    it['start_time'] += offset
                    it['end_time'] = it['start_time'] + mp3len
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])

                    offset += diff
                    set_process(f"[{idx+1}/{last_index+1}] Video speed -{srtmeta_item['speed_down']}")
                    if cut_clip == 0 and it['start_time'] == 0:
                        # set_process(f"当前是第一个，并且以0时间值开始，需要 clipmp4和endmp4 2个片段")
                        # 当前是第一个并且从头开始，不需要 startmp4, 共2个片段直接截取 clip 和 end
                        cut_from_video(ss="0",
                                       to="00:00:00.500" if wavlen < 500 else queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, pts=pts, out=clipmp4)
                        runffmpeg([
                            "-y",
                            "-ss",
                            queue_copy[idx]['endraw'].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c:v",
                            "copy",
                            f'{endmp4}'
                        ])
                    elif cut_clip == 0 and it['start_time'] > 0:
                        # set_process(f"当前是第一个，但不是以0时间值开始，需要 startmp4 clipmp4和endmp4 3个片段")
                        # 如果是第一个，并且不是从头开始的，则从原始提取开头的片段，startmp4 climp4 endmp4
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            "00:00:00.500" if it['start_time'] < 500 else queue_copy[idx]["startraw"].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c:v",
                            "copy",
                            f'{startmp4}'
                        ])
                        cut_from_video(ss=queue_copy[idx]['startraw'],
                                       to=ms_to_time_string(ms=queue_copy[idx]['start_time'] + 500).replace(',',
                                                                                                            '.') if wavlen < 500 else
                                       queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, pts=pts, out=clipmp4)
                        # 从原始提取结束 end
                        runffmpeg([
                            "-y",
                            "-ss",
                            queue_copy[idx]['endraw'].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c:v",
                            "copy",
                            f'{endmp4}'
                        ])
                    elif (idx == last_index) and queue_copy[idx]['end_time'] < source_mp4_total_length:
                        #  是最后一个，但没到末尾，后边还有片段
                        #  start部分从  tmp 里获取
                        # set_process(f"当前是最后一个，没到末尾，需要 startmp4和 clipmp4 和 endmp4")
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}',
                            "-c:v",
                            "copy",
                            f'{startmp4}'
                        ])
                        to_time = queue_copy[idx]['end_time']
                        ss_time = queue_copy[idx]['start_time']
                        if wavlen < 500:
                            to_time = queue_copy[idx]['start_time'] + 500
                            to_time = to_time if to_time < source_mp4_total_length else source_mp4_total_length
                            ss_time = ss_time if to_time - ss_time >= 500 else to_time - 500
                        cut_from_video(ss=ms_to_time_string(ms=ss_time).replace(',', '.'),
                                       to=ms_to_time_string(ms=to_time).replace(',', '.'),
                                       source=self.novoice_mp4, pts=pts, out=clipmp4)
                        if source_mp4_total_length - queue_copy[idx]['end_time'] < 500:
                            ss_time = ms_to_time_string(ms=source_mp4_total_length - 500).replace(',', '.')
                        else:
                            ss_time = queue_copy[idx]['endraw'].replace(',', '.')
                        runffmpeg([
                            "-y",
                            "-ss",
                            ss_time,
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c:v",
                            "copy",
                            f'{endmp4}'
                        ])
                    elif (idx == last_index) and queue_copy[idx]['end_time'] >= source_mp4_total_length and \
                            queue_copy[idx]['start_time'] < source_mp4_total_length:
                        # 是 最后一个，并且后边没有了,只有 startmp4 和 clip
                        # set_process(f"当前是最后一个，并且到达结尾，只需要 startmp4和 clipmp4 2个片段")
                        # start 需要从 tmp获取
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}',
                            "-c:v",
                            "copy",
                            f'{startmp4}'
                        ])

                        if source_mp4_total_length - queue_copy[idx]['start_time'] < 500:
                            ss_time = ms_to_time_string(ms=source_mp4_total_length - 500).replace(',', '.')
                        else:
                            ss_time = queue_copy[idx]['startraw'].replace(',', '.')
                        cut_from_video(ss=ss_time, to="", source=self.novoice_mp4, pts=pts,
                                       out=clipmp4)
                    elif cut_clip > 0 and queue_copy[idx]['start_time'] < source_mp4_total_length:
                        # 处于中间的其他情况，有前后中 3个
                        # start 需要从 tmp 获取
                        # set_process(f"当前是第{idx + 1}个，需要 startmp4和 clipmp4和endmp4 3个片段")
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-to",
                            "00:00:00.500" if wavlen < 500 else it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}',
                            "-c:v",
                            "copy",
                            f'{startmp4}'
                        ])
                        to_time = source_mp4_total_length if queue_copy[idx]['end_time'] > source_mp4_total_length else \
                        queue_copy[idx]['end_time']
                        if to_time - queue_copy[idx]['start_time'] < 500:
                            ss_time = ms_to_time_string(ms=to_time - 500).replace(',', '.')
                        else:
                            ss_time = queue_copy[idx]['startraw']
                        cut_from_video(ss=ss_time,
                                       to=ms_to_time_string(ms=to_time).replace(',', '.'), source=self.novoice_mp4,
                                       pts=pts, out=clipmp4)
                        # 从原始获取结束
                        if queue_copy[idx]['end_time'] < source_mp4_total_length:
                            if source_mp4_total_length - queue_copy[idx]['end_time'] < 500:
                                ss_time = ms_to_time_string(ms=source_mp4_total_length - 500).replace(',', '.')
                            else:
                                ss_time = queue_copy[idx]['endraw'].replace(',', '.')
                            runffmpeg([
                                "-y",
                                "-ss",
                                ss_time,
                                "-i",
                                f'{self.novoice_mp4}',
                                "-c:v",
                                "copy",
                                f'{endmp4}'
                            ])

                    # 合并这个3个
                    if os.path.exists(startmp4) and os.path.exists(endmp4) and os.path.exists(clipmp4):
                        runffmpeg(
                            ['-y', '-i', f'{startmp4}', '-i', f'{clipmp4}', '-i', f'{endmp4}', '-filter_complex',
                             '[0:v][1:v][2:v]concat=n=3:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264", '-crf',
                             '0', '-an', f'{novoice_mp4_tmp}'])
                        # set_process(f"3个合并")
                    elif os.path.exists(startmp4) and os.path.exists(clipmp4):
                        runffmpeg([
                            '-y', '-i', f'{startmp4}', '-i', f'{clipmp4}', '-filter_complex',
                            '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264", '-crf', '0',
                            '-an', f'{novoice_mp4_tmp}'])
                        # set_process(f"startmp4 和 clipmp4 合并")
                    elif os.path.exists(endmp4) and os.path.exists(clipmp4):
                        runffmpeg(['-y', '-i', f'{clipmp4}', '-i', f'{endmp4}', f'-filter_complex',
                                   f'[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264",
                                   '-crf', '0', '-an', f'{novoice_mp4_tmp}'])
                    cut_clip += 1
                    queue_params[idx] = it
                else:
                    # set_process(f"无需降速 {diff=}")
                    total_length += wavlen
                    it['start_time'] += offset
                    it['end_time'] = it['start_time'] + wavlen
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    queue_params[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
                set_process(f"[{line_num}] end")
                srtmeta.append(srtmeta_item)

            set_process(f"Origin:{source_mp4_total_length=} + offset:{offset} = {source_mp4_total_length + offset}")

            if os.path.exists(novoice_mp4_tmp):
                # os.unlink(self.novoice_mp4)
                shutil.copy2(novoice_mp4_tmp, self.novoice_mp4)
                # 总长度，单位ms
                try:
                    total_length = int(get_video_duration(self.novoice_mp4))
                except:
                    total_length=None
            if not total_length:
                total_length = source_mp4_total_length + offset
            set_process(f"New video:{total_length=}")
            if total_length < source_mp4_total_length - 500:
                try:
                    # 对视频末尾定格延长
                    if not self.novoicemp4_add_time(source_mp4_total_length - total_length):
                        set_process(transobj["moweiyanchangshibai"])
                    else:
                        set_process(f'{source_mp4_total_length - total_length}ms')
                except Exception as e:
                    set_process(f'{transobj["moweiyanchangshibai"]}:{str(e)}')
            # 重新修改字幕
            srt = ""
            try:
                for (idx, it) in enumerate(queue_params):
                    srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
                # 修改目标文件夹字幕
                with open(self.targetdir_target_sub, 'w',
                          encoding="utf-8") as f:
                    f.write(srt.strip())
            except Exception as e:
                set_process("[error]video speed down error " + str(e), 'error')
                return False
        except Exception as e:
            set_process("[error]video speed down error" + str(e), 'error')
            return False
        try:
            # 视频降速，肯定存在视频，不需要额外处理
            self.merge_audio_segments(segments, start_times, total_length)
        except Exception as e:
            set_process(f"[error]merge audio:seglen={len(segments)},starttimelen={len(start_times)} " + str(e), 'error')
            return False
        return True

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts, total_length):
        total_length = int(total_length * 1000)
        queue_copy = copy.deepcopy(queue_tts)
        def get_item(q):
            return {"text": q['text'], "role": q['role'], "rate": config.params["voice_rate"], "filename": q["filename"],
                    "tts_type": config.params['tts_type']}

        # 需要并行的数量3
        while len(queue_tts) > 0:
            if config.current_status != 'ing':
                return False
            try:
                tolist = [threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0)))]
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))

                for t in tolist:
                    t.start()
                for t in tolist:
                    t.join()
            except Exception as e:
                config.current_status = 'stop'
                set_process(f'[error]语音合成出错了:{str(e)}', 'error')
                return False
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if total_length > 0 and config.params['video_autorate']:
            return self.video_autorate_process(queue_copy, total_length)
        if len(queue_copy) < 1:
            set_process(f'text to speech，{queue_copy=}', 'error')
            return False
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            srtmeta = []
            for (idx, it) in enumerate(queue_copy):
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                srtmeta_item = {
                    'dubbing_time': -1,
                    'source_time': -1,
                    'speed_up': -1,
                    "text": it['text'],
                    "line": idx + 1
                }
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))

                    queue_copy[idx] = it
                    srtmeta.append(srtmeta_item)
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                mp3len = len(audio_data)

                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']

                if wavlen <= 0:
                    queue_copy[idx] = it
                    srtmeta.append(srtmeta_item)
                    continue
                # 新配音时长
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_up'] = 0
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                if diff > 0 and config.params["voice_autorate"]:
                    speed = mp3len / wavlen
                    speed = 1.8 if speed > 1.8 else round(speed, 2)
                    srtmeta_item['speed_up'] = speed
                    # 新的长度
                    mp3len = mp3len / speed
                    diff = mp3len - wavlen
                    if diff < 0:
                        diff = 0
                    set_process(f"dubbing speed + {speed}")
                    # 音频加速 最大加速2倍
                    audio_data = speed_change(audio_data, speed)
                    # 增加新的偏移
                    offset += diff
                elif diff > 0:
                    offset += diff
                    if config.params["voice_autorate"]:
                        pass
                        # set_process("已启用自动加速但无需加速")
                it['end_time'] = it['start_time'] + mp3len
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
                srtmeta.append(srtmeta_item)
            # 更新字幕
            srt = ""
            for (idx, it) in enumerate(queue_copy):
                srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
            # 字幕保存到目标文件夹一份
            with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
                f.write(srt.strip())
            # 保存字幕元信息
            # with open(f"{self.target_dir}/srt.json", 'w', encoding="utf-8") as f:
            #     f.write("dubbing_time=配音时长，source_time=原时长,speed_up=配音加速为原来的倍数\n-1表示无效，0代表未变化，无该字段表示跳过\n" + json.dumps(
            #         srtmeta))
            # 原音频长度大于0时，即只有存在原音频时，才进行视频延长
            if total_length > 0 and offset > 0 and queue_copy[-1]['end_time'] > total_length:
                # 判断 最后一个片段的 end_time 是否超出 total_length,如果是 ，则修改offset，增加
                offset = int(queue_copy[-1]['end_time'] - total_length)
                set_process(f"{offset=}>0，end add video frame {offset} ms")
                try:
                    # 对视频末尾定格延长
                    if not self.novoicemp4_add_time(offset):
                        offset = 0
                        set_process(f"[error]Failed to add extended video frame at the end, will remain unchanged, truncate audio, and do not extend video")
                    else:
                        pass
                        # set_process(f'视频延长成功')
                except Exception as e:
                    set_process(f"[error]Failed to add extended video frame at the end, will remain unchanged, truncate audio, and do not extend video:{str(e)}")
                    offset = 0
            else:
                pass
                # set_process(f"末尾不需要延长")
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times, 0 if total_length == 0 else total_length + offset)
        except Exception as e:
            set_process(f"[error] exec_tts text to speech:" + str(e), 'error')
            return False
        return True

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def compos_video(self):
        # 预先创建好的
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            return False

        # 需要配音
        if config.params['voice_role'] not in ['No', 'no', '-']:
            if not os.path.exists(self.targetdir_target_wav):
                set_process(f"[error] dubbing file error: {self.targetdir_target_wav}")
                return False
        # 需要字幕
        if config.params['subtitle_type'] > 0 and not os.path.exists(self.targetdir_target_sub):
            set_process(f"[error]no vail srt file {self.targetdir_target_sub}", 'error')
            return False
        if config.params['subtitle_type'] == 1:
            # 硬字幕 重新整理字幕，换行
            try:
                subs = get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                set_process(f'subtitles srt error:{str(e)}')
                return False
            maxlen = 36 if config.params['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
            subtitles = ""
            for it in subs:
                it['text'] = textwrap.fill(it['text'], maxlen)
                subtitles += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
                f.write(subtitles.strip())
            shutil.copy2(self.targetdir_target_sub,config.rootdir+"/tmp.srt")
            hard_srt="tmp.srt"
        # 有字幕有配音
        rs=False
        try:
            if config.params['voice_role'] != 'No' and config.params['subtitle_type'] > 0:
                if config.params['subtitle_type'] == 1:
                    set_process(f"dubbing & embed srt")
                    # 需要配音+硬字幕
                    rs=runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-c:v",
                        "libx264",
                        # "libx264",
                        "-c:a",
                        "aac",
                        # "pcm_s16le",
                        "-vf",
                        f"subtitles={hard_srt}",
                        # "-shortest",
                        os.path.normpath(self.targetdir_mp4),
                    ])
                else:
                    set_process(f"dubbing & srt")
                    # 配音+软字幕
                    rs=runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-sub_charenc",
                        "UTF-8",
                        "-f",
                        "srt",
                        "-i",
                        os.path.normpath(self.targetdir_target_sub),
                        "-c:v",
                        "libx264",
                        # "libx264",
                        "-c:a",
                        "aac",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={config.params['subtitle_language']}",
                        # "-shortest",
                        os.path.normpath(self.targetdir_mp4)
                    ])
            elif config.params['voice_role'] != 'No':
                # 配音无字幕
                set_process(f"dubbing")
                rs=runffmpeg([
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4),
                    "-i",
                    os.path.normpath(self.targetdir_target_wav),
                    "-c:v",
                    "copy",
                    # "libx264",
                    "-c:a",
                    "aac",
                    # "pcm_s16le",
                    # "-shortest",
                    os.path.normpath(self.targetdir_mp4)
                ])
            # 无配音 使用 novice.mp4 和 原始 wav合并
            elif config.params['subtitle_type'] == 1:
                # 硬字幕无配音 将原始mp4复制到当前文件夹下
                set_process(f"embed srt & no dubbing")
                rs=runffmpeg([
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4),
                    "-i",
                    os.path.normpath(self.targetdir_source_wav),
                    "-c:v",
                    "libx264",
                    # "libx264",
                    "-c:a",
                    "aac",
                    # "pcm_s16le",
                    "-vf",
                    f"subtitles={hard_srt}",
                    # "-shortest",
                    os.path.normpath(self.targetdir_mp4),
                ])
            elif config.params['subtitle_type'] == 2:
                # 软字幕无配音
                set_process(f"srt & no dubbing")
                rs=runffmpeg([
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4),
                    "-i",
                    os.path.normpath(self.targetdir_source_wav),
                    "-sub_charenc",
                    "UTF-8",
                    "-f",
                    "srt",
                    "-i",
                    os.path.normpath(self.targetdir_target_sub),
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    # "libx264",
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={config.params['subtitle_language']}",
                    # "-shortest",
                    os.path.normpath(self.targetdir_mp4)
                ])
        except Exception as e:
            set_process(f'{str(e)}','error')
            return False
        try:
            if os.path.exists(config.rootdir+"/tmp.srt"):
                os.unlink(config.rootdir+"/tmp.srt")
        except:
            pass
        return rs
