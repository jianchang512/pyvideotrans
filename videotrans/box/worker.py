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
from videotrans.util import tools
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
                 audio_ajust=False,
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
        self.audio_ajust = audio_ajust
        self.tmpdir = f'{homedir}/tmp'
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir, exist_ok=True)

    def run(self):
        config.box_tts = 'ing'
        # 字幕格式
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


    # 1. 将每个配音的实际长度加入 dubb_time
    #
    def _add_dubb_time(self, queue_tts):
        for i, it in enumerate(queue_tts):
            it['video_add']=0
            # 防止开始时间比上个结束时间还小
            if i > 0 and it['start_time'] < queue_tts[i - 1]['end_time']:
                it['start_time'] = queue_tts[i - 1]['end_time']
            # 防止结束时间小于开始时间
            if it['end_time'] < it['start_time']:
                it['end_time'] = it['start_time']
            # 保存原始
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            #记录原字母区间时长
            it['raw_duration']=it['end_time']-it['start_time']

            if it['end_time'] > it['start_time'] and os.path.exists(it['filename']) and os.path.getsize(it['filename']) > 0:
                it['dubb_time'] = len(AudioSegment.from_file(it['filename'], format="mp3"))
            else:
                #不存在配音
                it['dubb_time'] = 0
            queue_tts[i] = it

        return queue_tts

    #2.  移除原字幕多于配音的时长，实际是字幕结束时间向前移动，和下一条之间的空白更加多了
    def _remove_srt_silence(self,queue_tts):
        #如果需要移除多出来的静音
        for i,it in enumerate(queue_tts):
            # 配音小于 原时长，移除默认静音
            if it['dubb_time']>0 and it['dubb_time'] < it['raw_duration']:
                diff=it['raw_duration']-it['dubb_time']
                it['end_time']-=diff
                it['raw_duration']=it['dubb_time']
            queue_tts[i]=it
        return queue_tts
    # 3. 自动后延或前延以对齐
    def _auto_ajust(self, queue_tts):
        max_index = len(queue_tts) - 1

        for i, it in enumerate(queue_tts):
            # 如果存在配音文件并且时长大于0，才需要判断是否顺延
            if "dubb_time" not in it and it['dubb_time'] <= 0:
                continue
            # 配音时长如果大于原时长，才需要两侧延伸
            diff = it['dubb_time'] - it['raw_duration']
            if diff <= 0:
                continue
            # 需要两侧延伸

            # 最后一个，直接后延就可以
            if i == max_index:
                # 如果是最后一个，直接延长
                it['end_time'] += diff
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                #重新设定可用的字幕区间时长
                it['raw_duration']=it['end_time']-it['start_time']
                queue_tts[i] = it
                continue

            # 判断后边的开始时间比当前结束时间是否大于
            next_diff = queue_tts[i + 1]['start_time'] - it['end_time']
            if next_diff >= diff:
                # 如果大于0，有空白，添加
                it['end_time'] += diff
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                it['raw_duration']=it['end_time']-it['start_time']
                queue_tts[i] = it
                continue

            # 防止出错
            next_diff = 0 if next_diff < 0 else next_diff
            # 先向后延伸占完空白，然后再向前添加，
            it['end_time'] += next_diff
            # 判断是否存在前边偏移
            if it['start_time'] > 0:
                # 前面空白
                prev_diff = it['start_time'] if i == 0 else it['start_time'] - queue_tts[i - 1]['end_time']
                # 前面再添加最多 diff - next_diff
                it['start_time'] -= min(prev_diff, diff - next_diff)
                it['start_time'] = 0 if it['start_time'] < 0 else it['start_time']
            it['raw_duration']=it['end_time']-it['start_time']
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts


    #   移除2个字幕间的间隔 config.settings[remove_white_ms] ms
    def _remove_white_ms(self,queue_tts):
        offset=0
        for i,it in enumerate(queue_tts):
            if i>0:
                it['start_time']-=offset
                it['end_time']-=offset
                # 配音小于 原时长，移除默认静音
                dt=it['start_time']-queue_tts[i-1]['end_time']
                if dt>config.settings['remove_white_ms']:
                    diff=config.settings['remove_white_ms']
                    it['end_time']-=diff
                    it['start_time']-=diff
                    offset+=diff
                queue_tts[i]=it
        return queue_tts


    # 2. 先对配音加速，每条字幕信息中写入加速倍数 speed和延长的时间 add_time
    def _ajust_audio(self, queue_tts):
        # 遍历所有字幕条， 计算应该的配音加速倍数和延长的时间
        max_speed = config.settings['audio_rate']
        if max_speed>=100:
            max_speed=99

        #设置加速倍数
        for i, it in enumerate(queue_tts):
            it['speed'] = 0
            # 存在配音时进行处理 没有配音
            if it['dubb_time'] <= 0:
                queue_tts[i] = it
                continue
            # 字幕可用时长
            raw_duration = it['raw_duration']
            # 配音时长大于可用字幕时长，需加速
            diff = it['dubb_time'] - raw_duration
            # 存在原时长，并且新配音大于原时长，才需要加速,计算加速倍数 speed，并计算相对于原时长需要延长的时长add_time, 原时长不变
            # 配音时长 不大于 原时长，不处理
            if raw_duration <= 0 or diff <= 0:
                queue_tts[i] = it
                continue
            # 是否按照对齐的一半进行，用于音频加速和视频慢速同时起作用
            # 倍数上浮
            it['speed'] = round(it['dubb_time'] / raw_duration,2)
            if it['speed']<=1:
                it['speed']=0
                queue_tts[i]=it
                continue



            #     # 如果大于限制倍，则最大限制倍
            if max_speed> 1 and max_speed<it['speed']:
                it['speed']=max_speed

            if it['speed']<1:
                it['speed']=0
            print(f'[i={i+1}],配音时长={it["dubb_time"]},需加速{it["speed"]}')
            queue_tts[i] = it

        # 再次遍历，调整字幕开始结束时间对齐实际音频时长
        # 每次 start_time 和 end_time 需要添加的长度 offset 为当前所有 add_time 之和
        offset = 0
        for i, it in enumerate(queue_tts):

            #偏移增加
            it['start_time'] += offset
            # 结束时间还需要额外添加
            it['end_time'] +=offset

            if it['speed']<=1:
                # 不需要加速
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_tts[i] = it
                continue


            if it['speed'] >1:
                # 调整音频
                print(f'音频加速 speed={it["speed"]}')
                tmp_mp3 = os.path.join(self.tmpdir, f'{it["filename"]}-speed.mp3')
                speed_up_mp3(filename=it['filename'], speed=it['speed'], out=tmp_mp3)
                # 加速后时间
                mp3_len=len(AudioSegment.from_file(tmp_mp3, format="mp3"))
                raw_t=it['raw_duration']
                #加速后如果仍大于原时长，再移除末尾静音
                if mp3_len > raw_t:
                    tools.remove_silence_from_end(tmp_mp3)
                    add_time=len(AudioSegment.from_file(tmp_mp3, format="mp3"))-raw_t
                    print(f'加速并移除静音后仍多出来 add_time={add_time=}')
                    if add_time>0:
                        # 需要延长结束时间，以便字幕 声音对齐
                        it['end_time']+=add_time
                        offset += add_time
                        it['video_add']=add_time
                it['raw_duration']=it['end_time']-it['start_time']
                it['filename'] = tmp_mp3

            # 更改时间戳
            print(f'【i={i+1}】 加速{it["speed"]}')
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts


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

                # 1.首先添加配音时间
                queue_tts = self._add_dubb_time(queue_tts)

                # 2.移除字幕多于配音的时间，实际上是字幕结束时间前移，和下一条字幕空白更多
                if config.settings['remove_srt_silence']:
                    queue_tts=self._remove_srt_silence(queue_tts)

                # 3.是否需要 前后延展
                if self.audio_ajust:
                    queue_tts = self._auto_ajust(queue_tts)


                # 4. 如果需要配音加速
                if self.voice_autorate:
                    queue_tts = self._ajust_audio(queue_tts)

                # 5.从字幕间隔移除多余的毫秒数
                if config.settings['remove_white_ms']>0:
                    queue_tts=self._remove_white_ms(queue_tts)
                # 开始合并音频
                segments = []
                for i, it in enumerate(queue_tts):
                    if os.path.exists(it['filename']) and os.path.getsize(it['filename']) > 0:
                        segments.append(AudioSegment.from_file(it['filename'], format="mp3"))
                    else:
                        segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                self.merge_audio_segments(segments=segments,video_time=0,queue_tts=copy.deepcopy(queue_tts),out=f'{self.wavname}-{item["file"]}.wav')

            except Exception as e:
                errs+=1
                with open(f'{self.wavname}-error.txt','w',encoding='utf-8') as f:
                    f.write(f'srt文件 {item["file"]} 合成失败，原因为:{str(e)}\n\n原字幕内容为\n\n{item["text"]}')
            finally:
                percent=round(100*(n+1)/length,2)
                set_process_box(f'{percent}%','ing',func_name=self.func_name)
        return errs,length-errs


    def merge_audio_segments(self, *, segments=None, queue_tts=None, video_time=0,out=None):
        merged_audio = AudioSegment.empty()
        # start is not 0
        if queue_tts[0]['start_time'] > 0:
            silence_duration = queue_tts[0]['start_time']
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence
        # join
        offset=0
        for i,it in enumerate(queue_tts):
            segment = segments[i]
            the_dur=len(segment)
            #字幕可用时间
            raw_dur=it['raw_duration']
            it['start_time']+=offset
            it['end_time']+=offset

            diff=the_dur-raw_dur
            # 配音大于字幕时长，后延，延长时间
            if diff>=0:
                print(f'配音大于字幕时长{diff}ms, i={i+1}')
                it['end_time']+=diff
                offset+=diff
            else:
                #配音小于原时长，添加静音
                merged_audio += AudioSegment.silent(duration=abs(diff))


            if i > 0:
                silence_duration = it['start_time'] - queue_tts[i - 1]['end_time']
                # 前面一个和当前之间存在静音区间
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence
            it['startraw']=ms_to_time_string(ms=it['start_time'])
            it['endraw']=ms_to_time_string(ms=it['end_time'])
            queue_tts[i]=it
            merged_audio += segment

        if video_time > 0 and (len(merged_audio) < video_time):
            # 末尾补静音
            silence = AudioSegment.silent(duration=video_time - len(merged_audio))
            merged_audio += silence
        # 创建配音后的文件
        try:
            merged_audio.export(out, format="wav")
        except Exception as e:
            raise Exception(f'[error]merge_audio:{str(e)}')
        return len(merged_audio), queue_tts

    def post_message(self, type, text=""):
        set_process_box(text, type, func_name=self.func_name)


class FanyiWorker(QThread):

    def __init__(self, type, target_language, files, parent=None):
        super(FanyiWorker, self).__init__(parent)
        self.type = type
        self.target_language = target_language
        self.files = files
        self.srts = ""

    def run(self):
        # 开始翻译,从目标文件夹读取原始字幕
        set_process_box(f'start translate')
        config.box_trans = "ing"
        target=os.path.join(os.path.dirname(self.files[0]),'_translate')
        os.makedirs(target,exist_ok=True)
        for f in self.files:
            try:
                rawsrt = get_subtitle_from_srt(f, is_file=True)
            except Exception as e:
                set_process_box(f"\n{config.transobj['srtgeshierror']}:{f}" + str(e), 'error',func_name='fanyi_oneerror')
                continue
            try:
                set_process_box(f'正在翻译字幕{f}',func_name='fanyi_set_source')
                srt = run_trans(translate_type=self.type, text_list=rawsrt, target_language_name=self.target_language, set_p=False)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                with open(os.path.join(target,os.path.basename(f)),'w',encoding='utf-8') as f:
                    f.write(srts_tmp)
                set_process_box(srts_tmp, "end", func_name="fanyi_end")

            except Exception as e:
                set_process_box(f'翻译字幕{f}出错:{str(e)}', "error", func_name="fanyi_end")
        config.box_trans = "stop"
        set_process_box("", "end", func_name="fanyi_all")
