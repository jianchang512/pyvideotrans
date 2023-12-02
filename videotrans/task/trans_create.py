import copy
import json
import os
import re
import shutil
import textwrap
import threading
import time
from datetime import timedelta

import speech_recognition as sr
import whisper
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.configure.config import transobj, logger
from videotrans.translator import chatgpttrans, googletrans, baidutrans, tencenttrans, baidutrans_spider, deepltrans, \
    deeplxtrans
from videotrans.util.tools import runffmpeg, set_process, delete_files, delete_temp, match_target_amplitude, show_popup, \
    shorten_voice, \
    ms_to_time_string, get_subtitle_from_srt, get_lastjpg_fromvideo, get_video_fps, get_video_resolution, \
    is_novoice_mp4, cut_from_video, get_video_duration, text_to_speech, speed_change


class TransCreate():

    def __init__(self, obj):
        # 一条待处理的完整信息
        self.obj = obj
        self.step='prepare'
        # 仅提取字幕，不嵌入字幕，不配音，仅用于提取字幕
        #【从视频提取出字幕文件】
        # 选择视频文件，选择视频源语言，如果选择目标语言，则会输出翻译后的字幕文件，其他无需选择，开始执行
        self.only_srt = obj['subtitle_type'] < 1 and obj['voice_role'] in ['No','no','-']
        # 原始视频
        self.source_mp4 = self.obj['source_mp4'].replace('\\', '/')
        #去掉扩展名的视频名，做标识
        self.noextname = os.path.splitext(os.path.basename(self.source_mp4))[0]

        # 临时文件夹
        self.cache_folder = f"{config.rootdir}/tmp/{self.noextname}"
        # 分离出的原始音频文件
        self.source_wav = f"{self.cache_folder}/{self.noextname}.wav"
        # 配音后的tts音频
        self.tts_wav = f"{self.cache_folder}/tts-{self.noextname}.wav"
        # 翻译后的字幕文件-存于缓存
        self.sub_name = f"{self.cache_folder}/{self.noextname}.srt"
        self.novoice_mp4 = f"{self.cache_folder}/novoice.mp4"

        # 目标文件夹
        if not self.obj['target_dir']:
            self.target_dir = (os.path.dirname(self.source_mp4) + "/_video_out").replace('\\', '/')
        else:
            self.target_dir = self.obj['target_dir']
        self.target_dir += f"/{self.noextname}"

        # 创建文件夹
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)
        # 源语言字幕和目标语言字幕
        self.targetdir_source_sub = f"{self.target_dir}/{self.obj['source_language']}.srt"
        self.targetdir_target_sub = f"{self.target_dir}/{self.obj['target_language']}.srt"
        # 原wav和目标音频
        self.targetdir_source_wav = f"{self.target_dir}/{self.obj['source_language']}.wav"
        self.targetdir_target_wav = f"{self.target_dir}/{self.obj['target_language']}.wav"
        self.targetdir_mp4 = f"{self.target_dir}/{self.noextname}.mp4"

    # 启动执行入口
    def run(self):
        # 分离出音频 和 无声视频，若失败则停止
        if not self.split_wav_novicemp4():
            return set_process("分离音视频出错", 'error')

        # 识别提取出字幕，如果出错则停止,如果存在，则不需要识别
        # 识别成功后，原始字幕存于目标文件夹内
        # 如果不存在sub_name 或存在但无效，需要识别，其他无需识别
        if not os.path.exists(self.sub_name) or os.path.getsize(self.sub_name) ==0:
            if not self.recongn():
                return set_process("语音识别出错了", 'error')

        # 翻译字幕，如果设置了目标语言，则翻译字幕, 翻译出错则停止。未设置目标语言则不翻译并继续
        # 翻译后的字幕分别存于缓存和目标文件夹内
        # 需等待用户修改
        # 如果存在 tmp/下字幕,或目标语言没选择，或不存在源语言字幕，无需翻译
        #其他情况需要翻译
        if self.obj['target_language'] not in ['No', 'no', '-'] and not os.path.exists(self.sub_name) and  os.path.exists(self.targetdir_source_sub):
            self.step = 'translate'
            if not self.trans():
                return set_process("翻译出错.", 'error')

        # 如果选择了目标语言，则需要将字幕复制到目标语言，否则不复制。比如 仅将本地字幕嵌入视频，不需要翻译
        # 【本地已有字幕不配音直接嵌入视频】
        # 选择视频，然后将已有的字幕文件拖拽到右侧字幕区，目标语言选择 - 、配音色选择
        # No，开始执行
        if self.obj['target_language'] not in ['No', 'no', '-'] and not os.path.exists(self.targetdir_target_sub) and os.path.exists(self.sub_name):
            shutil.copy(self.sub_name, self.targetdir_target_sub)


        # 如果仅仅需要提取字幕（不配音、不嵌入字幕），到此返回
        #【从视频提取出字幕文件】
        #选择视频文件，选择视频源语言，如果选择目标语言，则会输出翻译后的字幕文件，其他无需选择，开始执行
        if self.only_srt:
            delete_temp(self.noextname)
            set_process(f"<br><strong>{self.source_mp4} 提取字幕结束</strong>")
            # 检测是否还有
            return True

        # 生成字幕后  等待是否执行后续 配音 合并 操作 等待倒计时
        # 如果需要配音，不需要则跳过，配音后的wav缓存和目标文件夹分别存储一份
        if self.obj['voice_role'] not in ['No', 'no', '-']:
            set_process(f"等待修改配音字幕/点击继续", "edit_subtitle")
            self.step = "dubbing"
            config.task_countdown=60
            while config.task_countdown > 0:
                if config.current_status != 'ing':
                    set_process("已停止", 'stop')
                    return
                # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                time.sleep(1)
                # 倒计时中
                config.task_countdown -= 1
                if config.task_countdown <= 60 and config.task_countdown>=0:
                    set_process(f"{config.task_countdown}秒后自动合并，你可以停止倒计时后去修改字幕，以便配音更准确",'show_djs')
            set_process('<br>倒计时停止,更新目标语言字幕','timeout_djs')
            time.sleep(3)

            try:
                set_process(f"<br><strong>开始配音操作:{self.obj['tts_type']},{self.obj['voice_role']}</strong><br>", 'logs')
                # 包含 音频自动加速和视频自动降速，创建 tts.wav
                res = self.before_tts()
            except Exception as e:
                set_process("[error]组装配音所需数据时出错:" + str(e), "error")
                return False
            try:
                if isinstance(res, tuple):
                    self.exec_tts(res[0], res[1])
            except Exception as e:
                set_process("[error]配音时出错:" + str(e), "error")
                if os.path.exists(self.tts_wav):
                    os.unlink(self.tts_wav)
                delete_files(self.cache_folder, '.mp3')
                delete_files(self.cache_folder, '.mp4')
                delete_files(self.cache_folder, '.png')
                return False


        # 最后一步合成
        try:
            set_process(f"<br><strong>进行最后一步组装处理</strong><br>", 'logs')
            self.step = 'compos'
            if self.compos_video():
                # 检测是否还有
                set_process(
                    f"<br><strong style='color:#00a67d;font-size:16px'>[{self.noextname}] 视频处理结束:相关素材可在目标文件夹内查看，含字幕文件、配音文件等</strong><br>",
                    'logs')
                delete_temp(self.noextname)
        except Exception as e:
            set_process(f"[error]:进行最终合并时出错:" + str(e), "error")
            delete_files(self.cache_folder,'.mp3')
            delete_files(self.cache_folder,'.mp4')
            delete_files(self.cache_folder,'.png')
            return False
        return True

    # 分离音频 和 novoice.mp4
    def split_wav_novicemp4(self):
        # 单独提前分离出 novice.mp4
        # 要么需要嵌入字幕 要么需要配音，才需要分离
        if not self.only_srt and not os.path.exists(self.novoice_mp4):
            ffmpegars = [
                "-y",
                "-i",
                f'{self.source_mp4}',
                "-an",
                f'{self.novoice_mp4}'
            ]
            threading.Thread(target=runffmpeg, args=(ffmpegars,), kwargs={"noextname": self.noextname}).start()

        # 如果不存在音频，则分离出音频
        if not os.path.exists(self.source_wav) or os.path.getsize(self.source_wav) == 0:
            set_process(f"{self.noextname} 分析视频数据", "logs")
            try:
                if runffmpeg([
                    "-y",
                    "-i",
                    f'{self.source_mp4}',
                    "-ac",
                    "1",
                    f'{self.source_wav}'
                ]) is None:
                    set_process(f'[error]{self.source_mp4}拆分音频出错，该视频中可能不存在有效音频数据', 'error')
                    return False
                shutil.copy2(self.source_wav, self.targetdir_source_wav)
            except Exception as e:
                set_process(f'拆分音频出错{str(e)}', 'error')
                return False
        return True

    # 识别出字幕
    def recongn(self):
        try:
            # 识别为字幕
            if self.obj['whisper_type'] == 'all':
                self.recognition_all()
            else:
                self.recognition_split()
            # 识别出的源语言字幕
            return True
        except Exception as e:
            set_process(f"语音识别出错:" + str(e), 'error')
            set_process("已停止", 'stop')
        return False

    # 翻译字幕
    def trans(self):
        try:
            # 等待编辑原字幕
            set_process("等待修改原语言字幕/继续", 'show_source_subtitle')
            config.task_countdown = 60
            while config.task_countdown > 0:
                if config.task_countdown <= 60 and config.task_countdown>=0:
                    set_process(f"{config.task_countdown} 秒后自动翻译，你可以停止倒计时后去修改字幕，以便翻译更准确",'show_djs')
                time.sleep(1)
                config.task_countdown-=1
            set_process("<br><strong>开始翻译字幕文件</strong><br>")
            set_process('<br>倒计时停止，清空字幕区文字','timeout_djs')
            time.sleep(3)
            self.srt_translation_srt()
            return True
        except Exception as e:
            set_process(f"文字翻译出错:" + str(e), 'error')
            set_process("已停止", 'stop')
        return False

    # split audio by silence
    def shorten_voice(self, normalized_sound):
        normalized_sound = match_target_amplitude(normalized_sound, -20.0)
        max_interval = 10000
        buffer = 500
        nonsilent_data = []
        audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(self.obj['voice_silence']),
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
            merged_audio.export(f'{self.target_dir}/{self.obj["target_language"]}-nocut.wav', format="wav")
            merged_audio = merged_audio[:total_duration]
        # 创建配音后的文件
        merged_audio.export(f"{self.cache_folder}/tts-{self.noextname}.wav", format="wav")
        shutil.copy(
            f"{self.cache_folder}/tts-{self.noextname}.wav",
            f"{self.target_dir}/{self.obj['target_language']}.wav"
        )
        return merged_audio

    # noextname 是去掉 后缀mp4的视频文件名字
    # 所有临时文件保存在 /tmp/noextname文件夹下
    # 分批次读取
    def recognition_split(self):
        set_process("<br>准备分割数据后进行语音识别")
        if config.current_status == 'stop':
            return False
        tmp_path = f'{self.cache_folder}/##{self.noextname}_tmp'
        if not os.path.isdir(tmp_path):
            try:
                os.makedirs(tmp_path, 0o777, exist_ok=True)
            except:
                show_popup(transobj["anerror"], transobj["createdirerror"])
        # 已存在字幕文件
        if os.path.exists(self.sub_name) and os.path.getsize(self.sub_name) > 0:
            set_process(f"{self.noextname} 字幕文件已存在，直接使用", 'logs')
            return
        normalized_sound = AudioSegment.from_wav(self.source_wav)  # -20.0
        nonslient_file = f'{tmp_path}/detected_voice.json'
        if os.path.exists(nonslient_file) and os.path.getsize(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            if config.current_status == 'stop':
                return False
            nonsilent_data = shorten_voice(normalized_sound)
            set_process(f"{self.noextname} 对音频文件按静音片段分割处理", 'logs')
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)
        r = sr.Recognizer()
        raw_subtitles = []
        offset = 0
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
            set_process(f"{self.noextname} 音频处理进度{time_covered:.1f}%", 'logs')
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            add_vol = 0
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format="wav")

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                audio_listened = r.record(source)
                if config.current_status == 'stop':
                    raise Exception("You stop it.")
                try:
                    options = {"download_root": config.rootdir + "/models"}
                    text = r.recognize_whisper(
                        audio_listened,
                        language="zh" if self.obj['detect_language'] == "zh-cn" or
                                         self.obj['detect_language'] == "zh-tw" else
                        self.obj['detect_language'],
                        model=self.obj['whisper_model'],
                        load_options=options
                    )
                except sr.UnknownValueError as e:
                    set_process("[error]:语音识别出错了:" + str(e))
                    continue
                except Exception as e:
                    set_process("[error]:语音识别出错了:" + str(e))
                    continue
                if config.current_status == 'stop':
                    raise Exception("You stop it.")
                text = f"{text.capitalize()}. ".replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)
                start = timedelta(milliseconds=start_time)
                
                stmp=str(start).split('.')
                if len(stmp)==2:
                    start=f'{stmp[0]},{int(int(stmp[-1])/1000)}'
                print(f'{str(start)}')
                end = timedelta(milliseconds=end_time)
                etmp=str(end).split('.')
                if len(etmp)==2:
                    end=f'{etmp[0]},{int(int(etmp[-1])/1000)}'
                raw_subtitles.append({"line": len(raw_subtitles) + 1, "time": f"{start} --> {end}", "text": text})
        set_process(f"字幕识别完成，共{len(raw_subtitles)}条字幕", 'logs')
        # 写入原语言字幕到目标文件夹
        self.save_srt_target(raw_subtitles, self.obj['source_language'])
        return True

    # 整体识别，全部传给模型
    def recognition_all(self):
        model = self.obj['whisper_model']
        language = self.obj['detect_language']
        set_process(f"<br>准备进行整体语音识别,可能耗时较久，请等待:{model}模型")
        try:
            model = whisper.load_model(model, download_root=config.rootdir + "/models")
            transcribe = model.transcribe(self.source_wav,
                                          language="zh" if language in ["zh-cn", "zh-tw"] else language, )
            segments = transcribe['segments']
            # 保留原始语言的字幕
            raw_subtitles = []
            offset = 0
            for (sidx, segment) in enumerate(segments):
                if config.current_status == 'stop' or config.current_status == 'end':
                    return
                segment['start'] = int(segment['start'] * 1000) + offset
                segment['end'] = int(segment['end'] * 1000) + offset
                if segment['start'] == segment['end']:
                    segment['end'] += 200
                    if sidx < len(segments) - 1 and (int(segments[sidx + 1]['start'] * 1000) < segment['end']):
                        offset += 200
                startTime = ms_to_time_string(ms=segment['start'])
                endTime = ms_to_time_string(ms=segment['end'])
                text = segment['text'].strip().replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)
                # 无有效字符
                if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(
                        text) <= 1:
                    continue
                # 原语言字幕
                raw_subtitles.append(
                    {"line": len(raw_subtitles) + 1, "time": f"{startTime} --> {endTime}", "text": text})
            set_process(f"字幕识别完成，等待翻译，共{len(raw_subtitles)}条字幕", 'logs')
            # 写入翻译前的原语言字幕到目标文件夹
            self.save_srt_target(raw_subtitles, self.obj['source_language'])
        except Exception as e:
            set_process(f"{model}模型整体识别出错了:{str(e)}", 'error')
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
            set_process(f"整理格式化原始字幕信息出错:"+str(e), 'error')
            return False
        if self.obj['translate_type'] == 'chatGPT':
            set_process(f"等待 chatGPT 返回响应", 'logs')
            try:
                rawsrt = chatgpttrans(rawsrt)
            except Exception as e:
                set_process(f'使用chatGPT翻译字幕时出错:{str(e)}','error')
                return False
        else:
            # 其他翻译，逐行翻译
            for (i, it) in enumerate(rawsrt):
                if config.current_status != 'ing':
                    return
                new_text = it['text']
                if self.obj['translate_type'] == 'google':
                    new_text = googletrans(it['text'],
                                           self.obj['source_language'],
                                           self.obj['target_language'])
                elif self.obj['translate_type'] == 'baidu':
                    new_text = baidutrans(it['text'], 'auto', self.obj['target_language_baidu'])
                elif self.obj['translate_type'] == 'tencent':
                    new_text = tencenttrans(it['text'], 'auto', self.obj['target_language_tencent'])
                elif self.obj['translate_type'] == 'baidu(noKey)':
                    new_text = baidutrans_spider(it['text'], 'auto', self.obj['target_language_baidu'])
                elif self.obj['translate_type'] == 'DeepL':
                    new_text = deepltrans(it['text'], self.obj['target_language_deepl'])
                elif self.obj['translate_type'] == 'DeepLX':
                    new_text = deeplxtrans(it['text'], self.obj['target_language_deepl'])
                new_text = new_text.replace('&#39;', "'")
                new_text = re.sub(r'&#\d+;', '', new_text)
                # 更新字幕区域
                set_process(f"{it['line']}\n{it['time']}\n{new_text}\n\n", "subtitle")
                it['text'] = new_text
                rawsrt[i] = it
        set_process(f"<br><strong>翻译完成</strong>")
        # 保存到 翻译后的 字幕 到tmp缓存
        self.save_srt_tmp(rawsrt)
        # 保存翻译后的字幕到目标文件夹
        self.save_srt_target(rawsrt, self.obj['target_language'])
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
    def save_srt_target(self, srtstr, language):
        # 是字幕列表形式，重新组装
        file = f'{self.target_dir}/{language}.srt'
        if isinstance(srtstr, list):
            txt = ""
            for it in srtstr:
                txt += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(file, 'w', encoding="utf-8") as f:
                f.write(txt.strip())
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        normalized_sound = AudioSegment.from_wav(self.source_wav)
        total_length = len(normalized_sound) / 1000
        if os.path.exists(self.tts_wav) and os.path.getsize(self.tts_wav)>0:
            shutil.copy2(self.tts_wav,self.targetdir_target_wav)
            return True
        # 整合一个队列到 exec_tts 执行
        if self.obj['voice_role'] != 'No':
            queue_tts = []
            # 获取字幕
            try:
                subs = get_subtitle_from_srt(self.sub_name)
            except Exception as e:
                set_process(f'准备配音数据，格式化字幕文件时出错:{str(e)}','error')
                return False
            rate = int(str(self.obj['voice_rate']).replace('%', ''))
            if rate >= 0:
                rate = f"+{rate}%"
            else:
                rate = f"{rate}%"
            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            for it in subs:
                if config.current_status != 'ing':
                    set_process('停止了', 'stop')
                    return True
                queue_tts.append({
                    "text": it['text'],
                    "role": self.obj['voice_role'],
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "rate": rate,
                    "startraw": it['startraw'],
                    "endraw": it['endraw'],
                    "filename": f"{self.cache_folder}/tts-{it['start_time']}.mp3"})
            return (queue_tts, total_length)
        return True

    # 延长 novoice.mp4  duration_ms 毫秒
    def novoicemp4_add_time(self, duration_ms):
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
            '-loop', '1', '-i', f'{img}', '-vf', f'fps={fps},scale={scale[0]}:{scale[1]}', '-c:v', 'libx264',
            '-crf', '0', '-to', f'{totime}', '-pix_fmt', f'yuv420p', '-y', f'{last_clip}'])
        if not rs:
            return False
        # 开始将 novoice_mp4 和 last_clip 合并
        os.rename(self.novoice_mp4, f'{self.novoice_mp4}.raw.mp4')
        return runffmpeg(
            ['-y', '-i', f'{self.novoice_mp4}.raw.mp4', '-i', f'{last_clip}', f'-filter_complex',
             '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', 'libx264', '-crf', '0', '-an',
             f'{self.novoice_mp4}'])

    # 视频自动降速处理
    def video_autorate_process(self, queue_params, source_mp4_total_length):
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
            set_process(f"原mp4长度={source_mp4_total_length=}")
            line_num = 0
            cut_clip = 0
            srtmeta=[]
            for (idx, it) in enumerate(queue_params):
                if config.current_status != 'ing':
                    return False
                # 原发音时间段长度
                wavlen = it['end_time'] - it['start_time']
                if wavlen == 0:
                    # 舍弃
                    continue
                line_num += 1
                srtmeta_item={
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
                    set_process(f"[error]: 此 {it['startraw']} - {it['endraw']} 时间段内字幕合成语音失败", 'logs')
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
                    if pts !=0:
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
                    set_process(f"该片段视频降速{srtmeta_item['speed_down']}倍")
                    if cut_clip == 0 and it['start_time'] == 0:
                        set_process(f"当前是第一个，并且以0时间值开始，需要 clipmp4和endmp4 2个片段")
                        # 当前是第一个并且从头开始，不需要 startmp4, 共2个片段直接截取 clip 和 end
                        cut_from_video(ss="0", to=queue_copy[idx]['endraw'], source=self.novoice_mp4, pts=pts, out=clipmp4)
                        runffmpeg([
                            "-y",
                            "-ss",
                            queue_copy[idx]['endraw'].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{endmp4}'
                        ])
                    elif cut_clip == 0 and it['start_time'] > 0:
                        set_process(f"当前是第一个，但不是以0时间值开始，需要 startmp4 clipmp4和endmp4 3个片段")
                        # 如果是第一个，并且不是从头开始的，则从原始提取开头的片段，startmp4 climp4 endmp4
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            queue_copy[idx]["startraw"].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{startmp4}'
                        ])
                        cut_from_video(ss=queue_copy[idx]['startraw'], to=queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, pts=pts, out=clipmp4)
                        # 从原始提取结束 end
                        runffmpeg([
                            "-y",
                            "-ss",
                            queue_copy[idx]['endraw'].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{endmp4}'
                        ])
                    elif (idx == last_index) and queue_copy[idx]['end_time'] < source_mp4_total_length:
                        #  是最后一个，但没到末尾，后边还有片段
                        #  开始部分从 todo 开始需要从 tmp 里获取
                        set_process(f"当前是最后一个，没到末尾，需要 startmp4和 clipmp4")
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}' if os.path.exists(novoice_mp4_tmp) else f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{startmp4}'
                        ])
                        cut_from_video(ss=queue_copy[idx]['startraw'], to=queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, pts=pts, out=clipmp4)
                        # 从原始获取末尾，如果当前是最后一个，并且原始里没有结束 从原始里 截取开始时间
                        if queue_copy[idx]['start_time'] + mp3len < source_mp4_total_length:
                            set_process(f"还需要endmp4")
                            runffmpeg([
                                "-y",
                                "-ss",
                                queue_copy[idx]['endraw'].replace(',', '.'),
                                "-i",
                                f'{self.novoice_mp4}',
                                "-c",
                                "copy",
                                f'{endmp4}'
                            ])
                        else:
                            set_process(f"不需要endmp4")
                    elif (idx == last_index) and queue_copy[idx]['end_time'] >= source_mp4_total_length and \
                            queue_copy[idx]['start_time'] < source_mp4_total_length:
                        # 是 最后一个，并且后边没有了,只有 startmp4 和 clip
                        set_process(f"当前是最后一个，并且到达结尾，只需要 startmp4和 clipmp4 2个片段")
                        # todo 需要从 tmp获取
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}' if os.path.exists(novoice_mp4_tmp) else f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{startmp4}'
                        ])

                        cut_from_video(ss=queue_copy[idx]['startraw'], to="", source=self.novoice_mp4, pts=pts,
                                       out=clipmp4)
                    elif cut_clip > 0 and queue_copy[idx]['start_time'] < source_mp4_total_length:
                        # 处于中间的其他情况，有前后中 3个
                        # start todo 需要从 tmp 获取
                        set_process(f"当前是第{idx + 1}个，需要 startmp4和 clipmp4和endmp4 3个片段")
                        runffmpeg([
                            "-y",
                            "-ss",
                            "0",
                            "-t",
                            it["startraw"].replace(',', '.'),
                            "-i",
                            f'{novoice_mp4_tmp}' if os.path.exists(novoice_mp4_tmp) else f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{startmp4}'
                        ])
                        cut_from_video(ss=queue_copy[idx]['startraw'],
                                       to="" if queue_copy[idx]['end_time'] > source_mp4_total_length else
                                       queue_copy[idx]['endraw'], source=self.novoice_mp4,
                                       pts=pts, out=clipmp4)
                        # 从原始获取结束
                        runffmpeg([
                            "-y",
                            "-ss",
                            queue_copy[idx]['endraw'].replace(',', '.'),
                            "-i",
                            f'{self.novoice_mp4}',
                            "-c",
                            "copy",
                            f'{endmp4}'
                        ])

                    # 合并这个3个
                    if os.path.exists(startmp4) and os.path.exists(endmp4) and os.path.exists(clipmp4):
                        runffmpeg(
                            ['-y', '-i', f'{startmp4}', '-i', f'{clipmp4}', '-i', f'{endmp4}', '-filter_complex',
                             '[0:v][1:v][2:v]concat=n=3:v=1:a=0[outv]', '-map', '[outv]', '-c:v', 'libx264', '-crf',
                             '0', '-an', f'{novoice_mp4_tmp}'])
                        set_process(f"3个合并")
                    elif os.path.exists(startmp4) and os.path.exists(clipmp4):
                        runffmpeg([
                            '-y', '-i', f'{startmp4}', '-i', f'{clipmp4}', '-filter_complex',
                            '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', 'libx264', '-crf', '0',
                            '-an', f'{novoice_mp4_tmp}'])
                        set_process(f"startmp4 和 clipmp4 合并")
                    elif os.path.exists(endmp4) and os.path.exists(clipmp4):
                        runffmpeg(['-y', '-i', f'{clipmp4}', '-i', f'{endmp4}', f'-filter_complex',
                                   f'[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', 'libx264',
                                   '-crf', '0', '-an', f'{novoice_mp4_tmp}'])
                        set_process(f"endmp4 和 clipmp4 合并")
                    cut_clip += 1
                    queue_params[idx] = it
                else:
                    set_process(f"无需降速 {diff=}")
                    total_length += wavlen
                    it['start_time'] += offset
                    it['end_time'] = it['start_time'] + wavlen
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    queue_params[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
                set_process(f"[{line_num}] 结束了====mp3.length={total_length=}=====<br>\n\n")
                srtmeta.append(srtmeta_item)

            set_process(f"<br>原长度:{source_mp4_total_length=} + offset = {source_mp4_total_length + offset}")
            total_length = source_mp4_total_length + offset

            if os.path.exists(novoice_mp4_tmp):
                os.rename(self.novoice_mp4, self.cache_folder + f"/novice.mp4.raw.mp4")
                os.rename(novoice_mp4_tmp, self.novoice_mp4)
                # 总长度，单位ms
                total_length = int(get_video_duration(self.novoice_mp4))
            if total_length is None:
                total_length = source_mp4_total_length + offset
            set_process(f"新视频实际长度:{total_length=}")
            # 重新修改字幕
            srt = ""
            try:
                for (idx, it) in enumerate(queue_params):
                    srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
                # 修改tmp临时字幕
                with open(self.sub_name, 'w', encoding='utf-8') as f:
                    f.write(srt.strip())
                # 修改目标文件夹字幕
                with open(self.targetdir_target_sub, 'w',
                          encoding="utf-8") as f:
                    f.write(srt.strip())
                # 保存srt元信息json
                with open(f"{self.target_dir}/srt.json", 'w', encoding="utf-8") as f:
                    f.write(
                        "dubbing_time=配音时长，source_time=原时长,speed_down=视频降速为原来的倍数\n-1表示无效，0代表未变化，无该字段表示跳过\n" + json.dumps(srtmeta))
            except Exception as e:
                set_process("[error]视频自动降速后更新字幕信息出错了 " + str(e), 'error')
                return False
        except Exception as e:
            set_process("[error]视频自动降速处理出错了" + str(e), 'error')
            return False
        try:
            # 视频降速，肯定存在视频，不需要额外处理
            self.merge_audio_segments(segments, start_times, total_length)
        except Exception as e:
            set_process(f"[error]音频合并出错了:seglen={len(segments)},starttimelen={len(start_times)} " + str(e), 'error')
            return False
        return True

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts, total_length):
        total_length = int(total_length * 1000)
        queue_copy = copy.deepcopy(queue_tts)
        def get_item(q):
            return {"text": q['text'], "role": q['role'], "rate": q['rate'], "filename": q["filename"],
                    "tts_type": self.obj['tts_type']}

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
        if total_length > 0 and self.obj['video_autorate']:
            return self.video_autorate_process(queue_copy, total_length)
        if len(queue_copy) < 1:
            return set_process(f'语言合成时出错了，{queue_copy=}', 'error')
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            srtmeta=[]
            for (idx, it) in enumerate(queue_copy):
                logger.info(f'\n\n{idx=},{it=}')
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                srtmeta_item={
                    'dubbing_time':-1,
                    'source_time':-1,
                    'speed_up':-1,
                    "text":it['text'],
                    "line":idx+1
                }
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                    set_process(f"[error]: 此 {it['startraw']} - {it['endraw']} 时间段内字幕合成语音失败", 'logs')

                    queue_copy[idx] = it
                    srtmeta.append(srtmeta_item)
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                mp3len = len(audio_data)

                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']

                if wavlen == 0:
                    queue_copy[idx] = it
                    srtmeta.append(srtmeta_item)
                    continue
                # 新配音时长
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_up'] = 0
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                if diff > 0 and self.obj['voice_autorate']:
                    speed = mp3len / wavlen
                    speed = 1.8 if speed > 1.8 else round(speed,2)
                    srtmeta_item['speed_up'] = speed
                    # 新的长度
                    mp3len = mp3len / speed
                    diff = mp3len - wavlen
                    if diff < 0:
                        diff = 0
                    set_process(f"自动加速配音 {speed} 倍<br>")
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
            # 更新字幕
            srt = ""
            for (idx, it) in enumerate(queue_copy):
                srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
            with open(self.sub_name, 'w', encoding="utf-8") as f:
                f.write(srt.strip())
            # 字幕保存到目标文件夹一份
            with open(self.targetdir_target_sub, 'w',
                      encoding="utf-8") as f:
                f.write(srt.strip())
            # 保存字幕元信息
            with open(f"{self.target_dir}/srt.json", 'w', encoding="utf-8") as f:
                f.write("dubbing_time=配音时长，source_time=原时长,speed_up=配音加速为原来的倍数\n-1表示无效，0代表未变化，无该字段表示跳过\n" + json.dumps(
                    srtmeta))
            # 原音频长度大于0时，即只有存在原音频时，才进行视频延长
            if total_length > 0 and offset > 0 and queue_copy[-1]['end_time'] > total_length:
                # 判断 最后一个片段的 end_time 是否超出 total_length,如果是 ，则修改offset，增加
                offset = int(queue_copy[-1]['end_time'] - total_length)
                set_process(f"{offset=}>0，需要末尾添加延长视频帧 {offset} ms")
                try:
                    # 对视频末尾定格延长
                    if not self.novoicemp4_add_time(offset):
                        offset = 0
                        set_process(f"[error]末尾添加延长视频帧失败，将保持原样，截断音频,不延长视频")
                    elif os.path.exists(self.novoice_mp4 + ".raw.mp4") and os.path.getsize(self.novoice_mp4) > 0:
                        set_process(f'视频延长成功')
                except Exception as e:
                    set_process(f"[error]末尾添加延长视频帧失败，将保持原样，截断音频，不延长视频:{str(e)}")
                    offset = 0
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times, 0 if total_length == 0 else total_length + offset)
        except Exception as e:
            set_process(f"[error] exec_tts 合成语音有出错:" + str(e),'error')
            return False
        return True

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def compos_video(self):
        # 如果尚未保存字幕到目标文件夹，则保存一份
        if os.path.exists(self.sub_name) and not os.path.exists(self.targetdir_target_sub):
            shutil.copy(self.sub_name, self.targetdir_target_sub)
        # target  output mp4 filepath
        # 预先创建好的
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            return False

        # 需要配音
        if self.obj['voice_role'] not in ['No','no','-']:
            if not os.path.exists(self.tts_wav) or os.path.getsize(self.tts_wav) == 0:
                set_process(f"[error] 配音文件创建失败: {self.tts_wav}", 'logs')
                return False
        # 需要字幕
        if self.obj['subtitle_type'] > 0 and (not os.path.exists(self.sub_name) or os.path.getsize(self.sub_name) == 0):
            set_process(f"[error]未创建成功有效的字幕文件 {self.sub_name}", 'error')
            return False
        if self.obj['subtitle_type'] == 1:
            # 硬字幕 重新整理字幕，换行
            try:
                subs = get_subtitle_from_srt(self.sub_name)
            except Exception as e:
                set_process(f'最终合并视频时，格式化硬字幕出错:{str(e)}')
                return False
            maxlen = 36 if self.obj['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
            subtitles = ""
            for it in subs:
                it['text'] = textwrap.fill(it['text'], maxlen)
                subtitles += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(self.sub_name, 'w', encoding="utf-8") as f:
                f.write(subtitles.strip())
            hard_srt = self.sub_name.replace('\\', '/').replace(':', '\\\\:')
        # 有字幕有配音
        if self.obj['voice_role'] != 'No' and self.obj['subtitle_type'] > 0:
            if self.obj['subtitle_type'] == 1:
                set_process(f"{self.noextname} 合成配音+硬字幕")
                # 需要配音+硬字幕
                runffmpeg([
                    "-y",
                    "-i",
                    f'{self.novoice_mp4}',
                    "-i",
                    f'{self.tts_wav}',
                    "-c:v",
                    "libx264",
                    # "libx264",
                    "-c:a",
                    "aac",
                    # "pcm_s16le",
                    "-vf",
                    f"subtitles={hard_srt}",
                    # "-shortest",
                    f'{self.targetdir_mp4}'
                ])
            else:
                set_process(f"{self.noextname} 合成配音+软字幕")
                # 配音+软字幕
                runffmpeg([
                    "-y",
                    "-i",
                    f'{self.novoice_mp4}',
                    "-i",
                    f'{self.tts_wav}',
                    "-sub_charenc",
                    "UTF-8",
                    "-f",
                    "srt",
                    "-i",
                    f'{self.sub_name}',
                    "-c:v",
                    "libx264",
                    # "libx264",
                    "-c:a",
                    "aac",
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={self.obj['subtitle_language']}",
                    # "-shortest",
                    f'{self.targetdir_mp4}'
                ])
        elif self.obj['voice_role'] != 'No':
            # 配音无字幕
            set_process(f"{self.noextname} 合成配音，无字幕")
            runffmpeg([
                "-y",
                "-i",
                f'{self.novoice_mp4}',
                "-i",
                f'{self.tts_wav}',
                "-c:v",
                "copy",
                # "libx264",
                "-c:a",
                "aac",
                # "pcm_s16le",
                # "-shortest",
                f'{self.targetdir_mp4}'
            ])
        # 无配音 使用 novice.mp4 和 原始 wav合并
        elif self.obj['subtitle_type'] == 1:
            # 硬字幕无配音 将原始mp4复制到当前文件夹下
            set_process(f"{self.noextname} 合成硬字幕，无配音")
            runffmpeg([
                "-y",
                "-i",
                f'{self.novoice_mp4}',
                "-i",
                f'{self.source_wav}',
                "-c:v",
                "libx264",
                # "libx264",
                "-c:a",
                "aac",
                # "pcm_s16le",
                "-vf",
                f"subtitles={hard_srt}",
                # "-shortest",
                f'{self.targetdir_mp4}',
            ])
        elif self.obj['subtitle_type'] == 2:
            # 软字幕无配音
            set_process(f"{self.noextname} 合成软字幕，无配音")
            runffmpeg([
                "-y",
                "-i",
                f'{self.novoice_mp4}',
                "-i",
                f'{self.source_wav}',
                "-sub_charenc",
                "UTF-8",
                "-f",
                "srt",
                "-i",
                f'{self.sub_name}',
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                # "libx264",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                f"language={self.obj['subtitle_language']}",
                # "-shortest",
                f'{self.targetdir_mp4}'
            ])
        return True
