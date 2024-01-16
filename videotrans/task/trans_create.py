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

# import whisper
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.configure.config import transobj, logger, homedir,Myexcept
from videotrans.translator import chatgpttrans, googletrans, baidutrans, tencenttrans, deepltrans,  deeplxtrans, azuretrans, geminitrans
from videotrans.util.tools import runffmpeg, set_process, match_target_amplitude, shorten_voice,ms_to_time_string, get_subtitle_from_srt, get_lastjpg_fromvideo,  is_novoice_mp4, cut_from_video, get_video_duration, text_to_speech,  delete_temp,     get_video_info, conver_mp4, split_novoice_byraw, split_audio_byraw, wav2m4a, m4a2wav, create_video_byimg,  concat_multi_mp4, speed_up_mp3

device = "cuda" if config.params['cuda'] else "cpu"




class TransCreate():

    def __init__(self, obj):
        print('00000')
        self.step = 'prepare'
        self.precent=0
        # 原始视频地址，等待转换为mp4格式
        self.wait_convermp4=None
        self.app_mode = obj['app_mode']
        # 原始视频
        self.source_mp4 = obj['source_mp4'].replace('\\', '/') if 'source_mp4' in obj else ""
        # 视频信息
        '''
        result={
            "video_fps":0,
            "video_codec_name":"h264",
            "audio_codec_name":"aac",
            "width":0,
            "height":0,
            "time":0
        }
        '''
        self.video_info = None

        # 没有视频，是根据字幕生成配音
        if not self.source_mp4:
            self.noextname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            config.btnkey="srt2wav"
        else:
            print('111')
            # 去掉扩展名的视频名，做标识
            self.noextname, ext = os.path.splitext(os.path.basename(self.source_mp4))
            print(f'111 {ext=}')
            # 不是mp4，先转为mp4
            if ext.lower() != '.mp4':
                out_mp4 = re.sub(rf'{ext}$', '.mp4', self.source_mp4)
                self.wait_convermp4=self.source_mp4
                self.source_mp4=out_mp4
                config.btnkey=self.source_mp4
            else:
                # 获取视频信息
                config.btnkey=self.source_mp4
                print(f'111 {self.source_mp4=}')
                try:
                    self.video_info = get_video_info(self.source_mp4)
                except Exception as e:
                    print(f'e=={str(e)}')
                print(f'111 video')
                if self.video_info is False:
                    raise Myexcept("get video_info error")
                # 不是标准mp4，先转码
                if self.video_info['video_codec_name'] != 'h264' or self.video_info['audio_codec_name'] != 'aac':
                    # 不是标准mp4，则转换为 libx264
                    out_mp4 = self.source_mp4[:-4] + "-libx264.mp4"
                    self.wait_convermp4=self.source_mp4
                    self.source_mp4 = out_mp4
        print('222')
        if not config.params['target_dir']:
            self.target_dir = f"{homedir}/only_dubbing" if not self.source_mp4 else (
                    os.path.dirname(self.source_mp4) + "/_video_out")
        else:
            self.target_dir = config.params['target_dir']
        print('333')
        # 全局目标，用于前台打开
        self.target_dir = self.target_dir.replace('\\','/').replace('//', '/')
        config.params['target_dir'] = self.target_dir
        # 真实具体到每个文件目标
        self.target_dir += f"/{self.noextname}"

        # 临时文件夹
        self.cache_folder = f"{config.rootdir}/tmp/{self.noextname}"
        # 分离出的原始音频文件
        self.source_wav = f"{self.cache_folder}/{self.noextname}.m4a"
        # 配音后的tts音频
        self.tts_wav = f"{self.cache_folder}/tts-{self.noextname}.m4a"
        # 翻译后的字幕文件-存于缓存
        self.sub_name = f"{self.cache_folder}/{self.noextname}.srt"


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
        self.targetdir_source_wav = f"{self.target_dir}/{config.params['source_language']}.m4a"
        self.targetdir_target_wav = f"{self.target_dir}/{config.params['target_language']}.m4a"
        self.targetdir_mp4 = f"{self.target_dir}/{self.noextname}.mp4"
        # 如果存在字幕，则视为目标字幕，直接生成，不再识别和翻译
        if "subtitles" in obj and obj['subtitles'].strip():
            with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
                f.write(obj['subtitles'].strip())

    # 启动执行入口
    def run(self):
        print('444')
        if config.current_status != 'ing':
            raise Myexcept("Had stop")
        if self.wait_convermp4:
            #需要转换格式
            set_process(transobj['kaishiyuchuli'])
            self.precent=1
            conver_mp4(self.wait_convermp4,self.source_mp4)
            self.video_info=get_video_info(self.source_mp4)

        set_process(self.target_dir, 'set_target_dir')
        ##### 开始分离
        self.step='split_start'
        self.split_wav_novicemp4()
        self.precent=5
        self.step='split_end'

        #### 开始识别
        self.step='regcon_start'
        try:
            self.recongn()
        except Exception as e:
            raise Exception(f'recogn error:{str(e)}')
        self.step='regcon_end'

        ##### 翻译阶段
        self.step = 'translate_start'
        self.trans()
        self.step = 'translate_end'


        # 如果存在目标语言字幕，并且存在 配音角色，则需要配音
        self.step = "dubbing_start"
        self.dubbing()
        self.step = 'dubbing_end'

        # 最后一步合成
        self.step = 'compos_start'
        self.hebing()
        self.step = 'compos_end'

    # 分离音频 和 novoice.mp4
    def split_wav_novicemp4(self):
        # 存在视频 , 不是 tiqu/tiqu_no/hebing
        if not self.source_mp4 or not os.path.exists(self.source_mp4):
            return True
        if self.app_mode == 'hebing':
            shutil.copy2(self.source_mp4, self.novoice_mp4)
            config.queue_novice[self.noextname] = 'end'
            return True

        # 单独提前分离出 novice.mp4
        # 要么需要嵌入字幕 要么需要配音，才需要分离
        if not os.path.exists(self.novoice_mp4):
            threading.Thread(target=split_novoice_byraw,
                             args=(self.source_mp4, self.novoice_mp4, self.noextname)).start()
        else:
            config.queue_novice[self.noextname] = 'end'

        # 如果不存在音频，则分离出音频
        if not os.path.exists(self.targetdir_source_wav):
            split_audio_byraw(self.source_mp4, self.targetdir_source_wav)
        return True

    # 识别出字幕
    def recongn(self):
        #####识别阶段 存在已识别后的字幕，并且不存在目标语言字幕，则更新替换界面字幕
        if not os.path.exists(self.targetdir_target_sub) and os.path.exists(self.targetdir_source_sub):
            # 通知前端替换字幕
            with open(self.targetdir_source_sub, 'r', encoding="utf-8") as f:
                set_process(f.read().strip(), 'replace_subtitle')
            return True
        # 如果不存在视频，或存在已识别过的，或存在目标语言字幕 或合并模式，不需要识别
        if not self.source_mp4 or \
                os.path.exists(self.targetdir_source_sub) or \
                os.path.exists(self.targetdir_target_sub) or \
                self.app_mode == 'hebing':
            return True
        # 分离未完成，需等待
        while not os.path.exists(self.targetdir_source_wav):
            set_process(transobj["running"])
            time.sleep(1)
        # 识别为字幕
        if config.params['whisper_type'] == 'all':
            return self.recognition_all()
        else:
            return self.recognition_split()

    # 翻译字幕
    def trans(self):
        # 如果存在字幕，并且存在目标语言字幕，则前台直接使用该字幕替换
        if self.source_mp4 and os.path.exists(self.targetdir_target_sub):
            # 通知前端替换字幕
            with open(self.targetdir_target_sub, 'r', encoding="utf-8") as f:
                set_process(f.read().strip(), 'replace_subtitle')
        # 是否需要翻译，不是 tiqu_no/hebing，存在识别后字幕并且不存在目标语言字幕，并且原语言和目标语言不同，则需要翻译
        if self.app_mode in ['tiqu_no', 'hebing'] or \
                os.path.exists(self.targetdir_target_sub) or \
                not os.path.exists(self.targetdir_source_sub) or \
                config.params['target_language'] in ['No', 'no', '-'] or\
                config.params['target_language'] == config.params['source_language']:
            return True


        # 等待编辑原字幕后翻译
        set_process(transobj["xiugaiyuanyuyan"], 'edit_subtitle')
        config.task_countdown = config.settings['OPTIM']['countdown_sec']
        while config.task_countdown > 0:
            if config.task_countdown <= config.settings['OPTIM']['countdown_sec'] and config.task_countdown >= 0:
                set_process(f"{config.task_countdown} {transobj['jimiaohoufanyi']}", 'show_djs')
            time.sleep(1)
            config.task_countdown -= 1
        set_process('', 'timeout_djs')
        time.sleep(2)
        self.srt_translation_srt()

    # 配音处理
    def dubbing(self):
        # 不需要配音
        if self.app_mode in ['tiqu','tiqu_no','hebing'] or \
                config.params['voice_role'] in ['No', 'no', '-'] or \
                os.path.exists(self.targetdir_target_wav) or \
                not os.path.exists(self.targetdir_target_sub):
            return True

        set_process(transobj["xiugaipeiyinzimu"], "edit_subtitle")
        config.task_countdown = config.settings['OPTIM']['countdown_sec']
        while config.task_countdown > 0:
            if config.current_status != 'ing':
                raise Myexcept(transobj["tingzhile"])
            # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
            time.sleep(1)
            # 倒计时中
            config.task_countdown -= 1
            if config.task_countdown <= config.settings['OPTIM']['countdown_sec'] and config.task_countdown >= 0:
                set_process(f"{config.task_countdown}{transobj['zidonghebingmiaohou']}", 'show_djs')
        set_process('', 'timeout_djs')
        time.sleep(3)
        try:
            res = self.before_tts()
            if isinstance(res, tuple):
                self.exec_tts(res[0], res[1])
        except Exception as e:
            delete_temp(self.noextname)
            raise Myexcept("[error] tts" + str(e))

    # 合并操作
    def hebing(self):
        if self.app_mode in ['tiqu','tiqu_no','peiyin'] or not self.source_mp4:
            return True
        try:
            self.compos_video()
        except Exception as e:
            delete_temp(self.noextname)
            raise Myexcept(f"[error] hebing compose:last step error " + str(e))

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
        wavfile = self.cache_folder + "/target.wav"
        merged_audio.export(wavfile, format="wav")
        wav2m4a(wavfile, self.targetdir_target_wav)
        return merged_audio

    # noextname 是去掉 后缀mp4的视频文件名字
    # 所有临时文件保存在 /tmp/noextname文件夹下
    # 分批次读取
    def recognition_split(self):
        set_process(transobj['fengeyinpinshuju'])
        if config.current_status == 'stop':
            return False
        tmp_path = f'{self.cache_folder}/##{self.noextname}_tmp'
        if not os.path.isdir(tmp_path):
            try:
                os.makedirs(tmp_path, 0o777, exist_ok=True)
            except:
                raise Myexcept(transobj["createdirerror"])
        wavfile = self.cache_folder + "/tmp.wav"
        m4a2wav(self.targetdir_source_wav, wavfile)
        normalized_sound = AudioSegment.from_wav(wavfile)  # -20.0
        nonslient_file = f'{tmp_path}/detected_voice.json'
        if os.path.exists(nonslient_file) and os.path.getsize(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            if config.current_status == 'stop':
                raise Myexcept("Has stop")
            nonsilent_data = shorten_voice(normalized_sound)
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)

        r = WhisperModel(config.params['whisper_model'], device=device,
                         compute_type="int8" if device == 'cpu' else "int8_float16",
                         download_root=config.rootdir + "/models",num_workers=os.cpu_count(),cpu_threads=os.cpu_count(), local_files_only=True)
        raw_subtitles = []
        # offset = 0
        language = "zh" if config.params['detect_language'] == "zh-cn" or config.params[
            'detect_language'] == "zh-tw" else config.params['detect_language']
        for i, duration in enumerate(nonsilent_data):
            if config.current_status == 'stop':
                raise Myexcept("Has stop")
            start_time, end_time, buffered = duration
            # start_time += offset
            # end_time += offset
            if start_time == end_time:
                end_time += 200
                # 如果加了200后，和下一个开始重合，则偏移
                # if (i < len(nonsilent_data) - 1) and nonsilent_data[i + 1][0] < end_time:
                #     offset += 200
            # 进度
            if self.precent<60:
                self.precent+=(i+1)*20/len(nonsilent_data)
            set_process(f"{transobj['yuyinshibiejindu']}")
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            audio_chunk = normalized_sound[start_time:end_time]
            audio_chunk.export(chunk_filename, format="wav")


            if config.current_status != 'ing':
                raise Myexcept("Has stop .")
            text = ""
            try:
                segments, _ = r.transcribe(chunk_filename,
                                           beam_size=5,
                                           language=language)
                for t in segments:
                    text += t.text + " "
            except Exception as e:
                set_process("[error]:" + str(e))
                continue

            if config.current_status == 'stop':
                raise Myexcept("Has stop it.")
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
            line = len(raw_subtitles) + 1
            set_process(f"{line}\n{start} --> {end}\n{text}\n\n", 'subtitle')
            raw_subtitles.append({"line": line, "time": f"{start} --> {end}", "text": text})
        set_process(f"{transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs')
        # 写入原语言字幕到目标文件夹
        print(raw_subtitles)
        self.save_srt_target(raw_subtitles, self.targetdir_source_sub)
        return True

    # 整体识别，全部传给模型
    def recognition_all(self):
        language = "zh" if config.params['detect_language'] in ["zh-cn", "zh-tw"] else config.params['detect_language']
        set_process(f"{config.params['whisper_model']} {transobj['kaishishibie']}, audio time {round(self.video_info['time']/1000)}s")
        down_root=os.path.normpath(config.rootdir + "/models")
        print(f'{down_root}')
        try:
            model = WhisperModel(config.params['whisper_model'], device=device,
                                 compute_type="int8" if device == 'cpu' else "int8_float16",
                                 download_root=down_root,num_workers=os.cpu_count(),
                                 cpu_threads=os.cpu_count(),
                                 local_files_only=True)
            wavfile = self.cache_folder + "/tmp.wav"
            m4a2wav(self.targetdir_source_wav, wavfile)
            segments, _ = model.transcribe(wavfile,
                                           beam_size=5,
                                           vad_filter=True,
                                           vad_parameters=dict(
                                               min_silence_duration_ms=int(config.params['voice_silence']),
                                               max_speech_duration_s=15), language=language)


            # 保留原始语言的字幕
            raw_subtitles = []
            offset = 0
            sidx = -1
            for segment in segments:
                if config.current_status != 'ing':
                    raise Myexcept("Had stop")
                sidx += 1
                start = int(segment.start * 1000) + offset
                end = int(segment.end * 1000) + offset
                if start == end:
                    end += 200
                    # if sidx < total_len - 1 and (int(segments[sidx + 1].start * 1000) < end):
                    #     offset += 200
                startTime = ms_to_time_string(ms=start)
                endTime = ms_to_time_string(ms=end)
                text = segment.text.strip().replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)
                # 无有效字符
                if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(text) <= 1:
                    continue
                # 原语言字幕
                s={"line": len(raw_subtitles) + 1, "time": f"{startTime} --> {endTime}", "text": text}
                raw_subtitles.append(s)
                set_process(f'{s["line"]}\n{startTime} --> {endTime}\n{text}\n\n','subtitle')
                set_process(f'{transobj["zimuhangshu"]} {s["line"]}')
                if self.precent<60:
                    self.precent+=0.05

        except Exception as e:
            raise Exception(f'whole all {str(e)}')
        set_process(transobj['yuyinshibiewancheng'], 'logs')
        # 写入翻译前的原语言字幕到目标文件夹
        self.save_srt_target(raw_subtitles, self.targetdir_source_sub)

    # 处理翻译,完整字幕由 src翻译为 target
    def srt_translation_srt(self):
        # 如果不存在原字幕，或已存在目标语言字幕则跳过，比如使用已有字幕，无需翻译时
        if not os.path.exists(self.targetdir_source_sub) or os.path.exists(self.targetdir_target_sub):
            return True
        set_process(transobj['starttrans'])
        # 开始翻译,从目标文件夹读取原始字幕
        rawsrt = get_subtitle_from_srt(self.targetdir_source_sub, is_file=True)

        if config.params['translate_type'] == 'chatGPT':
            set_process(f"waitting chatGPT", 'logs')
            rawsrt = chatgpttrans(rawsrt, config.params['target_language_chatgpt'])
        elif config.params['translate_type'] == 'Azure':
            set_process(f"waitting Azure ", 'logs')
            rawsrt = azuretrans(rawsrt, config.params['target_language_azure'])
        elif config.params['translate_type'] == 'Gemini':
            set_process(f"waitting Gemini", 'logs')
            rawsrt = geminitrans(rawsrt, config.params['target_language_gemini'])
        else:
            # 其他翻译，逐行翻译
            split_size = config.settings['OPTIM']['trans_thread']
            srt_lists = [rawsrt[i:i + split_size] for i in range(0, len(rawsrt), split_size)]
            # 存放翻译后结果
            trans_list=[]
            for (index,item) in enumerate(srt_lists):
                # 等待翻译的多行文字
                jd=round(20*(index+1)/len(srt_lists),1)
                if self.precent<75:
                    self.precent+=jd
                set_process(f"{transobj['starttrans']}")
                wait_text=[]
                for (i,it) in enumerate(item):
                    wait_text.append(it['text'].strip().replace("\n",'.'))
                wait_text="\n".join(wait_text)
                # 翻译
                new_text=""
                if config.params['translate_type'] == 'google':
                    new_text = googletrans(wait_text,
                                           config.params['source_language'],
                                           config.params['target_language'])
                elif config.params['translate_type'] == 'baidu':
                    new_text = baidutrans(wait_text, 'auto', config.params['target_language_baidu'])
                elif config.params['translate_type'] == 'tencent':
                    new_text = tencenttrans(wait_text, 'auto', config.params['target_language_tencent'])
                elif config.params['translate_type'] == 'DeepL':
                    new_text = deepltrans(wait_text, config.params['target_language_deepl'])
                elif config.params['translate_type'] == 'DeepLX':
                    new_text = deeplxtrans(wait_text, config.params['target_language_deepl'])
                if not new_text:
                    raise Myexcept("translation is error")
                trans_text = re.sub(r'&#\d+;', '', new_text).replace('&#39;', "'").split("\n")
                srt_str=""
                for (i,it) in enumerate(item):
                    if i<=len(trans_text)-1:
                        item[i]['text']=trans_text[i]
                        srt_str+=f"{it['line']}\n{it['time']}\n{trans_text[i]}\n\n"
                    else:
                        srt_str+=f"{it['line']}\n{it['time']}\n{item['text']}\n\n"
                set_process(srt_str, "subtitle")
                trans_list.extend(item)
        # 保存翻译后的字幕到目标文件夹
        self.save_srt_target(rawsrt, self.targetdir_target_sub)
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
                set_process(txt.strip(), 'replace_subtitle')
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        total_length = self.video_info['time'] if os.path.exists(self.targetdir_source_wav) else 0
        # 整合一个队列到 exec_tts 执行
        if config.params['voice_role'] not in ['No', 'no', '-']:
            queue_tts = []
            # 获取字幕
            try:
                subs = get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                raise Myexcept(f'[error] before tts srt error:{str(e)}')

            rate = int(str(config.params['voice_rate']).replace('%', ''))
            if rate >= 0:
                rate = f"+{rate}%"
            else:
                rate = f"{rate}%"
                # 取出设置的每行角色
            line_roles = config.params["line_roles"] if "line_roles" in config.params else None
            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            for it in subs:
                if config.current_status != 'ing':
                    raise Myexcept(transobj['tingzhile'])
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
        set_process(f'{transobj["shipinmoweiyanchang"]} {duration_ms}ms')
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Myexcept("not novoice mp4")
        # 截取最后一帧图片
        img = f'{self.cache_folder}/last.jpg'
        # 截取的图片组成 时长 duration_ms的视频
        last_clip = f'{self.cache_folder}/last_clip.mp4'
        # 取出最后一帧创建图片
        get_lastjpg_fromvideo(self.novoice_mp4, img)
        # 取出帧率
        fps = self.video_info['video_fps']
        if not fps:
            fps = 30
        # 取出分辨率
        scale = [self.video_info['width'], self.video_info['height']]

        # 创建 ms 格式
        totime = ms_to_time_string(ms=duration_ms).replace(',', '.')
        create_video_byimg(img=img, fps=fps, scale=scale, totime=totime, out=last_clip)

        # 开始将 novoice_mp4 和 last_clip 合并
        shutil.copy2(self.novoice_mp4, f'{self.novoice_mp4}.raw.mp4')
        concat_multi_mp4(filelist=[f'{self.novoice_mp4}.raw.mp4', last_clip], out=self.novoice_mp4)
        try:
            os.unlink(f'{self.novoice_mp4}.raw.mp4')
        except:
            pass
        return True

    # 视频自动降速处理
    def video_autorate_process(self, queue_params, source_mp4_total_length):
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Myexcept('not novoice mp4')
        segments = []
        start_times = []
        # 预先创建好的
        queue_copy = copy.deepcopy(queue_params)
        total_length = 0
        # 处理过程中不断变化的 novoice_mp4
        novoice_mp4_tmp = f"{self.cache_folder}/novoice_tmp.mp4"
        tmppert = f"{self.cache_folder}/tmppert.mp4"
        tmppert2 = f"{self.cache_folder}/tmppert2.mp4"
        tmppert3 = f"{self.cache_folder}/tmppert3.mp4"
        # 上一个片段的结束时间，用于判断是否需要复制上一个和当前2个片段中间的片段
        last_endtime = 0
        offset = 0
        try:
            # 增加的时间，用于 修改字幕里的开始显示时间和结束时间
            last_index = len(queue_params) - 1
            line_num = 0
            cut_clip = 0
            # 如果字幕开始时间大于0，则先去获取0到字幕开始时间的视频片段
            if queue_copy[0]['start_time'] > 0:
                cut_from_video(ss="0", to=queue_copy[0]['startraw'], source=self.novoice_mp4, out=novoice_mp4_tmp)
                last_endtime = queue_copy[0]['start_time']
            for (idx, it) in enumerate(queue_params):
                if config.current_status != 'ing':
                    raise Myexcept("Had stop")
                jd=round((idx+1)*20/(last_index+1),1)
                if self.precent<85:
                    self.precent+=jd
                # 原字幕时间段
                wavlen = it['end_time'] - it['start_time']
                line_num += 1
                # 开始时间加偏移
                it['start_time'] += offset
                # 该片段配音失败
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    it['end_time'] = it['start_time'] + wavlen
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=wavlen))
                    queue_params[idx] = it
                    logger.error(f'配音失败  {it}')
                    continue

                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                # 新发音长度
                mp3len = len(audio_data)
                # 先判断，如果 新时长大于旧时长，需要处理
                diff = mp3len - wavlen
                logger.info(f'\n\n{idx=},{mp3len=},{wavlen=},{diff=}')
                # 新时长大于旧时长，视频需要降速播放
                set_process(f"[{idx + 1}/{last_index + 1}] {transobj['shipinjiangsu']} {diff if diff>0 else 0}ms")
                if diff > 0:
                    it['end_time'] = it['start_time'] + mp3len
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    offset += diff
                    # 调整视频，新时长/旧时长
                    pts = round(mp3len / wavlen, 2)

                    # 当前是第一个需要慢速的
                    if cut_clip == 0:
                        logger.info(f'cut_clip=0, {last_endtime=},{pts=}')
                        # 如果也是视频从0开始的第一个
                        if last_endtime == 0:
                            # 第一个
                            pts = round(mp3len / queue_copy[idx]['end_time'], 2)
                            cut_from_video(ss="0",
                                           to=queue_copy[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=novoice_mp4_tmp)
                            logger.info(f'cut_clip=0,last_endtime==0,{pts=},当前是第一个需要慢速的,也是视频从0开始的第一个')
                        else:
                            logger.info(f'cut_clip=0, {last_endtime=}>0')
                            # 如果当前开始大于上次结束，中间有片段
                            if queue_copy[idx]['start_time'] > last_endtime:
                                logger.info(f'\t start_time > last_endtime  中间有片段')
                                cut_from_video(ss=ms_to_time_string(ms=last_endtime),
                                               to=queue_copy[idx]['startraw'],
                                               source=self.novoice_mp4, out=tmppert)
                                cut_from_video(ss=queue_copy[idx]['startraw'], to=queue_copy[idx]['endraw'],
                                               source=self.novoice_mp4, pts=pts, out=tmppert2)
                                concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert, tmppert2], out=tmppert3)
                                os.unlink(novoice_mp4_tmp)
                                os.rename(tmppert3, novoice_mp4_tmp)
                            else:
                                # 中间无片段
                                logger.info(f'\tstart_time <= last_endtime and 中间无片段')
                                cut_from_video(ss=queue_copy[idx]['startraw'], to=queue_copy[idx]['endraw'],
                                               source=self.novoice_mp4, pts=pts, out=tmppert)
                                concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert], out=tmppert2)
                                os.unlink(novoice_mp4_tmp)
                                os.rename(tmppert2, novoice_mp4_tmp)
                        cut_clip += 1
                    else:
                        logger.info(f'cut_clip>0, {cut_clip=} ,{last_endtime=}')
                        cut_clip += 1
                        # 判断中间是否有
                        pert = queue_copy[idx]['start_time'] - last_endtime
                        if pert > 0:
                            # 和上个片段中间有片段
                            logger.info(f'{pert=}>0,中间有片段')
                            pdlist=[novoice_mp4_tmp]
                            if queue_copy[idx]['start_time']>queue_copy[idx - 1]['end_time']:
                                cut_from_video(ss=queue_copy[idx - 1]['endraw'], to=queue_copy[idx]['startraw'],
                                           source=self.novoice_mp4, out=tmppert)
                                pdlist.append(tmppert)
                            cut_from_video(ss=queue_copy[idx]['startraw'],
                                           to=queue_copy[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=tmppert2)
                            pdlist.append(tmppert2)
                            concat_multi_mp4(filelist=pdlist, out=tmppert3)
                            os.unlink(novoice_mp4_tmp)
                            os.rename(tmppert3, novoice_mp4_tmp)
                        else:
                            # 和上个片段间中间无片段
                            logger.info(f'pert==0,中间无片段')
                            pdlist=[novoice_mp4_tmp]
                            # if queue_copy[idx]['start_time']>queue_copy[idx - 1]['end_time']:
                            cut_from_video(ss=queue_copy[idx]['startraw'], to=queue_copy[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=tmppert)
                            pdlist.append(tmppert)
                            concat_multi_mp4(filelist=pdlist, out=tmppert2)
                            os.unlink(novoice_mp4_tmp)
                            os.rename(tmppert2, novoice_mp4_tmp)
                    last_endtime = queue_copy[idx]['end_time']
                    queue_params[idx] = it
                else:
                    # 不需要慢速
                    logger.info(f'diff<=0,不需要降速')
                    it['end_time'] = it['start_time'] + wavlen
                    it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    queue_params[idx] = it
                    if last_endtime == 0:
                        logger.info(f'last_endtime=0,是第一个片段')
                        # 是第一个视频片段
                        cut_from_video(ss="0",
                                       to=queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, out=novoice_mp4_tmp)
                    else:
                        # 不是第一个
                        logger.info(f'{last_endtime=}>0，不是第一个片段')
                        cut_from_video(ss=ms_to_time_string(ms=last_endtime),
                                       to=queue_copy[idx]['endraw'],
                                       source=self.novoice_mp4, out=tmppert)
                        concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert], out=tmppert2)
                        os.unlink(novoice_mp4_tmp)
                        os.rename(tmppert2, novoice_mp4_tmp)
                    last_endtime = queue_copy[idx]['end_time']

                start_times.append(it['start_time'])
                segments.append(audio_data)
        except Exception as e:
            raise Myexcept(f"[error]{transobj['mansuchucuo']}:" + str(e))

        if last_endtime < queue_copy[-1]['end_time']:
            logger.info(f'处理循环完毕，但未到结尾 last_endtime < end_time')
            cut_from_video(ss=queue_copy[-1]['endraw'], to="", source=self.novoice_mp4,
                           out=tmppert)
            concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert], out=tmppert2)
            os.unlink(novoice_mp4_tmp)
            os.rename(tmppert2, novoice_mp4_tmp)
        set_process(f"Origin:{source_mp4_total_length=} + offset:{offset} = {source_mp4_total_length + offset}")

        # if os.path.exists(novoice_mp4_tmp) and os.path.getsize(novoice_mp4_tmp) > 0:
        shutil.copy2(novoice_mp4_tmp, self.novoice_mp4)
        # 总长度，单位ms
        total_length = int(get_video_duration(self.novoice_mp4))
        set_process(f'[1] {self.novoice_mp4=},,{total_length=}')
        if not total_length or total_length == 0:
            total_length = source_mp4_total_length + offset
        set_process(f'[2] {self.novoice_mp4=},,{total_length=}')
        set_process(f'[3] {source_mp4_total_length=},,{offset=}')
        set_process(f"{transobj['xinshipinchangdu']}:{source_mp4_total_length + offset}ms")
        if total_length < source_mp4_total_length + offset:
            try:
                # 对视频末尾定格延长
                self.novoicemp4_add_time(source_mp4_total_length + offset - total_length)
            except Exception as e:
                raise Myexcept(f'[novoicemp4_add_time]{transobj["moweiyanchangshibai"]}:{str(e)}')
        # 重新修改字幕
        srt = ""
        for (idx, it) in enumerate(queue_params):
            srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
        # 修改目标文件夹字幕
        with open(self.targetdir_target_sub, 'w',
                  encoding="utf-8") as f:
            f.write(srt.strip())

        # 视频降速，肯定存在视频，不需要额外处理
        self.merge_audio_segments(segments, start_times, source_mp4_total_length + offset)
        return True

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts, total_length):
        total_length = int(total_length)
        queue_copy = copy.deepcopy(queue_tts)

        def get_item(q):
            return {"text": q['text'], "role": q['role'], "rate": config.params["voice_rate"],
                    "filename": q["filename"], "tts_type": config.params['tts_type']}

        # 需要并行的数量3
        n_total=len(queue_tts)
        n=0
        while len(queue_tts) > 0:
            if config.current_status != 'ing':
                raise Myexcept('Had stop')
            try:
                tolist=[]
                for i in range(config.settings['OPTIM']['dubbing_thread']):
                    if len(queue_tts) > 0:
                        tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))
                for t in tolist:
                    t.start()
                for t in tolist:
                    n+=1
                    jd=round(n*10/n_total,1)
                    if self.precent<80:
                        self.precent+=jd
                    set_process(f'{transobj["kaishipeiyin"]} [{n}/{n_total}]')
                    t.join()
            except Exception as e:
                raise Myexcept(f'[error]exec_tts:{str(e)}')

        if config.current_status != 'ing':
            raise Myexcept('Had stop')
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if total_length > 0 and config.params['video_autorate']:
            return self.video_autorate_process(queue_copy, total_length)
        if len(queue_copy) < 1:
            raise Myexcept(f'text to speech，{queue_copy=}')

        # 偏移时间，用于每个 start_time 增减
        offset = 0
        # 将配音和字幕时间对其，修改字幕时间
        for (idx, it) in enumerate(queue_copy):
            # 如果有偏移，则添加偏移
            it['start_time'] += offset
            it['end_time'] += offset
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            jd=round((idx+1)*10/n_total,1)
            if self.precent<85:
                self.precent+=jd
            if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                start_times.append(it['start_time'])
                segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                queue_copy[idx] = it
                continue
            audio_data = AudioSegment.from_file(it['filename'], format="mp3")
            mp3len = len(audio_data)
            # 原字幕发音时间段长度
            wavlen = it['end_time'] - it['start_time']
            if wavlen <= 0:
                queue_copy[idx] = it
                continue
            # 新配音大于原字幕里设定时长
            diff = mp3len - wavlen

            if config.params["voice_autorate"]:
                # 需要加速并根据加速调整字幕时间 字幕时间 时长时间不变
                if diff > 0:
                    speed = mp3len / wavlen
                    # 新的长度
                    tmp_mp3 = os.path.join(self.cache_folder, f'{it["filename"]}.mp3')
                    speed_up_mp3(filename=it['filename'], speed=speed, out=tmp_mp3)
                    # mp3 降速
                    set_process(f"dubbing speed + {speed}")
                    # 音频加速 最大加速2倍
                    audio_data = AudioSegment.from_file(tmp_mp3, format="mp3")
            elif diff > 0:
                offset += diff
                it['end_time'] += diff

            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            queue_copy[idx] = it
            start_times.append(it['start_time'])
            segments.append(audio_data)
        # 更新字幕
        srt = ""
        for (idx, it) in enumerate(queue_copy):
            srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
        # 字幕保存到目标文件夹一份
        with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
            f.write(srt.strip())
        try:
            # 原音频长度大于0时，即只有存在原音频时，才进行视频延长
            if total_length > 0 and queue_copy[-1]['end_time'] > total_length:
                # 判断 最后一个片段的 end_time 是否超出 total_length,如果是 ，则修改offset，增加
                offset = int(queue_copy[-1]['end_time'] - total_length)
                total_length += offset
                # 对视频末尾定格延长
                self.novoicemp4_add_time(offset)
                set_process(f'{transobj["shipinjiangsu"]} {offset}ms')
        except Exception as e:
            raise Myexcept(f"[error] exec_tts text to speech:" + str(e))
        self.merge_audio_segments(segments, start_times, total_length)
        return True

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def compos_video(self):
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Myexcept("not novoice mp4")
        # 需要配音,选择了角色，并且不是 提取模式 合并模式
        if config.params['voice_role'] not in ['No', 'no', '-'] and self.app_mode not in ['tiqu', 'tiqu_no', 'hebing']:
            if not os.path.exists(self.targetdir_target_wav):
                raise Myexcept(f"[error] dubbing file error: {self.targetdir_target_wav}")
        # 需要字幕
        if config.params['subtitle_type'] > 0 and not os.path.exists(self.targetdir_target_sub):
            raise Myexcept(f"[error]no vail srt file {self.targetdir_target_sub}")
        if self.precent<95:
            self.precent+=1
        if config.params['subtitle_type'] == 1:
            # 硬字幕 重新整理字幕，换行
            try:
                subs = get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                raise Myexcept(f'subtitles srt error:{str(e)}')

            maxlen = 36 if config.params['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
            subtitles = ""
            for it in subs:
                it['text'] = textwrap.fill(it['text'], maxlen)
                subtitles += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            with open(self.targetdir_target_sub, 'w', encoding="utf-8") as f:
                f.write(subtitles.strip())
            shutil.copy2(self.targetdir_target_sub, config.rootdir + "/tmp.srt")
            hard_srt = "tmp.srt"
        if self.precent<95:
            self.precent+=1
        # 有字幕有配音
        rs = False
        try:
            if config.params['voice_role'] not in ['No', 'no', '-'] and config.params['subtitle_type'] > 0:
                if config.params['subtitle_type'] == 1:
                    set_process(transobj['peiyin-yingzimu'])
                    # 需要配音+硬字幕
                    rs = runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "copy",
                        "-vf",
                        f"subtitles={hard_srt}",
                        os.path.normpath(self.targetdir_mp4),
                    ], de_format="nv12")
                else:
                    set_process(transobj['peiyin-ruanzimu'])
                    # 配音+软字幕
                    rs = runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        # "-sub_charenc",
                        # "UTF-8",
                        # "-f",
                        # "srt",
                        "-i",
                        os.path.normpath(self.targetdir_target_sub),
                        "-c:v",
                        "copy",
                        # "libx264",
                        "-c:a",
                        "copy",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={config.params['subtitle_language']}",
                        # "-shortest",
                        os.path.normpath(self.targetdir_mp4)
                    ])
            elif config.params['voice_role'] not in ['No', 'no', '-']:
                # 配音无字幕
                set_process(transobj['onlypeiyin'])
                rs = runffmpeg([
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4),
                    "-i",
                    os.path.normpath(self.targetdir_target_wav),
                    "-c:v",
                    "copy",
                    # "libx264",
                    "-c:a",
                    "copy",
                    # "pcm_s16le",
                    # "-shortest",
                    os.path.normpath(self.targetdir_mp4)
                ])
            # 无配音 使用 novice.mp4 和 原始 wav合并
            elif config.params['subtitle_type'] == 1:
                set_process(transobj['onlyyingzimu'])
                cmd = [
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4)
                ]
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append('-i')
                    cmd.append(os.path.normpath(self.targetdir_source_wav))
                cmd.append('-c:v')
                cmd.append('libx264')
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append('-c:a')
                    cmd.append('copy')
                cmd += [
                    "-vf",
                    f"subtitles={hard_srt}",
                    os.path.normpath(self.targetdir_mp4),
                ]
                rs = runffmpeg(cmd, de_format="nv12")
            elif config.params['subtitle_type'] == 2:
                # 软字幕无配音
                set_process(transobj['onlyruanzimu'])
                cmd = [
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4)
                ]
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append("-i")
                    cmd.append(os.path.normpath(self.targetdir_source_wav))
                cmd += [
                    # "-sub_charenc",
                    # "UTF-8",
                    # "-f",
                    # "srt",
                    "-i",
                    os.path.normpath(self.targetdir_target_sub),
                    "-c:v",
                    "copy"]
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append('-c:a')
                    cmd.append('copy')
                cmd += ["-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={config.params['subtitle_language']}",
                        os.path.normpath(self.targetdir_mp4)
                        ]
                rs = runffmpeg(cmd)
        except Exception as e:
            raise Myexcept(f'[error] compos error:{str(e)}')
        if self.precent<100:
            self.precent=99
        try:
            if os.path.exists(config.rootdir + "/tmp.srt"):
                os.unlink(config.rootdir + "/tmp.srt")
        except:
            pass
        self.precent=100
        return rs
