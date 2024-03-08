import copy
import datetime
import hashlib
import os
import re
import shutil
import sys
import textwrap
import threading
import time

# import whisper
import urllib

import requests
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import transobj, logger, homedir, Myexcept
from videotrans.recognition import run as run_recogn
from videotrans.tts import run as run_tts
from videotrans.translator import run as  run_trans, get_audio_code, get_subtitle_code, GOOGLE_NAME
from videotrans.util import tools
from videotrans.util.tools import runffmpeg, set_process, ms_to_time_string, get_subtitle_from_srt, \
    get_lastjpg_fromvideo, is_novoice_mp4, cut_from_video, get_video_duration, delete_temp, \
    get_video_info, conver_mp4, split_novoice_byraw, split_audio_byraw, wav2m4a, create_video_byimg, concat_multi_mp4, \
    speed_up_mp3, backandvocal, cut_from_audio, get_clone_role, get_audio_time, concat_multi_audio, format_time


class TransCreate():

    def __init__(self, obj):
        self.step = 'prepare'
        self.precent = 0
        # 原始视频地址，等待转换为mp4格式
        self.wait_convermp4 = None
        self.app_mode = obj['app_mode']
        self.device = "cuda" if config.params['cuda'] else "cpu"
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
        self.del_sourcemp4 = False

        # 没有视频，是根据字幕生成配音
        if config.params['back_audio'] and os.path.exists(config.params['back_audio']):
            self.background_music = config.params['back_audio']
        else:
            self.background_music = None
        if not self.source_mp4 or self.app_mode == 'peiyin':
            self.source_mp4 = ''
            self.noextname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.precent = 40
        else:
            # 去掉扩展名的视频名，做标识
            self.noextname, ext = os.path.splitext(os.path.basename(self.source_mp4))
            # 如果源视频或目标目录含有空格 特殊字符，重命名并移动
            rs, newmp4, basename = tools.rename_move(self.source_mp4, is_dir=False)
            if rs:
                self.source_mp4 = newmp4
                self.noextname = basename
                self.del_sourcemp4 = True

            if self.app_mode not in ['tiqu', 'tiqu_no']:
                #else:
                # 获取视频信息
                try:
                    self.video_info = get_video_info(self.source_mp4)
                except Exception as e:
                    print(f'e=={str(e)}')

                if self.video_info is False:
                    raise Myexcept("get video_info error")

        if self.source_mp4:
            self.btnkey = self.source_mp4
        else:
            self.btnkey = "srt2wav"

        if config.params['target_dir']:
            rs, newdir, _ = tools.rename_move(config.params['target_dir'], is_dir=True)
            if rs:
                config.params['target_dir'] = newdir
                set_process(config.transobj['qianyiwenjian'], 'rename')

        if not config.params['target_dir']:
            self.target_dir = f"{homedir}/only_dubbing" if not self.source_mp4 else (
                    os.path.dirname(self.source_mp4) + "/_video_out")
        else:
            self.target_dir = config.params['target_dir']

        # 全局目标，用于前台打开
        self.target_dir = self.target_dir.replace('\\', '/').replace('//', '/')
        config.params['target_dir'] = self.target_dir
        # 真实具体到每个文件目标
        self.target_dir = os.path.join(self.target_dir, self.noextname).replace('\\', '/')

        # 临时文件夹
        self.cache_folder = f"{config.rootdir}/tmp/{self.noextname}"

        # 创建文件夹
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder, exist_ok=True)
        # 源语言字幕和目标语言字幕
        # 获取原语言代码和目标语言代码
        if "mode" in obj and obj['mode'] == "cli":
            self.source_language_code = config.params['source_language']
            self.target_language_code = config.params['target_language']
        else:
            # 仅作为文件名标识
            self.source_language_code, self.target_language_code = config.rev_langlist[
                                                                       config.params['source_language']] if \
                                                                       config.params['source_language'] != '-' else '-', \
                                                                   config.rev_langlist[
                                                                       config.params['target_language']] if \
                                                                       config.params['target_language'] != '-' else '-'

        # 如果存在 config.params['source_language'],则获取语音识别检测语言
        # 检测字幕原始语言
        self.detect_language = None
        self.subtitle_language = None
        if config.params['source_language'] != '-':
            self.detect_language = get_audio_code(show_source=config.params['source_language'])
        if config.params['target_language'] != '-':
            self.subtitle_language = get_subtitle_code(show_target=config.params['target_language'])

        self.novoice_mp4 = f"{self.target_dir}/novoice.mp4"
        self.targetdir_source_sub = f"{self.target_dir}/{self.source_language_code}.srt"
        self.targetdir_target_sub = f"{self.target_dir}/{self.target_language_code}.srt"
        # 原wav和目标音频
        self.targetdir_source_wav = f"{self.target_dir}/{self.source_language_code}.m4a"
        # 配音后的音频文件
        self.targetdir_target_wav = f"{self.target_dir}/{self.target_language_code}.m4a"
        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if config.params['voice_role'] != 'No' and self.source_language_code == self.target_language_code:
            self.targetdir_target_wav = f"{self.target_dir}/{self.target_language_code}-dubbing.m4a"

        self.targetdir_mp4 = f"{self.target_dir}/{self.noextname}.mp4"

        # 分离出的原始音频文件
        if config.params['is_separate']:
            # 如果保留背景，则转为 wav格式， 以便后续分离
            self.targetdir_source_wav = f"{self.target_dir}/{self.source_language_code}.wav"
            # 背景音乐
            self.targetdir_source_instrument = f"{self.target_dir}/instrument.wav"
            # 转为8k采样率，降低文件
            self.targetdir_source_vocal = f"{self.target_dir}/vocal.wav"
            self.targetdir_source_regcon = f"{self.target_dir}/vocal8000.wav"
            if os.path.exists(self.targetdir_source_regcon) and os.path.getsize(self.targetdir_source_regcon) == 0:
                os.unlink(self.targetdir_source_regcon)
        else:
            self.targetdir_source_vocal = self.targetdir_source_wav
            self.source_separate = self.source_back = self.source_vocal = None

        # 如果存在字幕，则视为目标字幕，直接生成，不再识别和翻译
        if "subtitles" in obj and obj['subtitles'].strip():
            sub_file = self.targetdir_target_sub
            if config.params['source_language'] != config.params['target_language'] and config.params[
                'source_language'] != '-' and config.params['target_language'] != '-':
                # 原始和目标语言都存在，并且不相等，需要翻译，作为待翻译字幕
                sub_file = self.targetdir_source_sub
            with open(sub_file, 'w', encoding="utf-8",errors="ignore") as f:
                f.write(obj['subtitles'].strip())
        if os.path.exists(self.targetdir_source_sub) and os.path.getsize(self.targetdir_source_sub) == 0:
            os.unlink(self.targetdir_source_sub)
        if os.path.exists(self.targetdir_target_sub) and os.path.getsize(self.targetdir_target_sub) == 0:
            os.unlink(self.targetdir_target_sub)
        if os.path.exists(self.targetdir_source_wav) and os.path.getsize(self.targetdir_source_wav) == 0:
            os.unlink(self.targetdir_source_wav)

        if os.path.exists(self.targetdir_target_wav) and os.path.getsize(self.targetdir_target_wav) == 0:
            os.unlink(self.targetdir_target_wav)

    # 启动执行入口
    def run(self):
        config.settings = config.parse_init()
        if config.current_status != 'ing':
            raise Myexcept("stop")
        if config.params['is_separate'] and config.params['tts_type'] == 'clone-voice':
            set_process(transobj['test clone voice'])
            try:
                get_clone_role(True)
            except Exception as e:
                raise Exception(str(e))

        self.precent += 1


        set_process(self.target_dir, 'set_target_dir')
        ##### 开始分离
        # 禁止修改字幕
        set_process("", "disabled_edit")
        self.step = 'split_start'
        self.split_wav_novicemp4()
        # self.precent += 5
        self.step = 'split_end'

        #### 开始识别
        self.step = 'regcon_start'
        self.recogn()
        self.step = 'regcon_end'
        if self.app_mode=='tiqu_no':
            return True

        ##### 翻译阶段
        self.step = 'translate_start'
        # 翻译暂停时允许修改字幕，翻译开始后禁止修改
        self.trans()
        self.step = 'translate_end'
        if self.app_mode=='tiqu':
            return True

        # 如果存在目标语言字幕，并且存在 配音角色，则需要配音
        self.step = "dubbing_start"
        # 配音开始前允许修改，开始后禁止修改
        self.dubbing()
        self.step = 'dubbing_end'
        if self.app_mode=='peiyin':
            return True


        # 最后一步合成
        self.step = 'compos_start'
        self.hebing()
        self.step = 'compos_end'
        set_process('', 'allow_edit')
    # 分离音频 和 novoice.mp4
    def split_wav_novicemp4(self):
        # 存在视频 , 不是 tiqu/tiqu_no/hebing
        if not self.source_mp4 or not os.path.exists(self.source_mp4) or self.app_mode=='peiyin':
            return True
        if self.app_mode == 'hebing':
            shutil.copy2(self.source_mp4, self.novoice_mp4)
            config.queue_novice[self.noextname] = 'end'
            return True

        # 单独提前分离出 novice.mp4
        # 要么需要嵌入字幕 要么需要配音，才需要分离 tiqu tiqu_no 不需要
        if self.app_mode not in ['tiqu', 'tiqu_no']:
            threading.Thread(target=split_novoice_byraw,
                             args=(self.source_mp4, self.novoice_mp4, self.noextname)).start()
        else:
            config.queue_novice[self.noextname] = 'end'

        # 如果不存在音频，则分离出音频
        # 添加是否保留背景选项
        if config.params['is_separate'] and config.params['voice_role'] != 'No' and not os.path.exists(
                self.targetdir_source_regcon):
            split_audio_byraw(self.source_mp4, self.targetdir_source_wav, True)
            if not os.path.exists(self.targetdir_source_vocal):
                # 分离失败
                self.targetdir_source_regcon = self.targetdir_source_vocal = self.targetdir_source_wav
                self.source_separate = self.source_back = self.source_vocal = None
                config.params['is_separate'] = False
        else:
            try:
                split_audio_byraw(self.source_mp4, self.targetdir_source_wav)
            except:
                raise Exception('从视频中提取声音失败，请检查视频中是否含有音轨，或该视频是否存在编码问题' if config.defaulelang=='zh' else 'Failed to extract sound from video, please check if the video contains an audio track or if there is an encoding problem with that video')
        return True

    # 识别出字幕
    def recogn(self):
        set_process(transobj["kaishishibie"])
        #####识别阶段 存在已识别后的字幕，并且不存在目标语言字幕，则更新替换界面字幕
        if not os.path.exists(self.targetdir_target_sub) and os.path.exists(self.targetdir_source_sub):
            # 通知前端替换字幕
            with open(self.targetdir_source_sub, 'r', encoding="utf-8",errors="ignore") as f:
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
        try:
            self.precent+=5
            raw_subtitles = run_recogn(
                type=config.params['whisper_type'],
                audio_file=self.targetdir_source_wav if not config.params[
                    'is_separate'] else self.targetdir_source_regcon,
                detect_language=self.detect_language,
                cache_folder=self.cache_folder,
                model_name=config.params['whisper_model'],
                model_type=config.params['model_type'],
                is_cuda=config.params['cuda'],
                inst=self)
        except Exception as e:
            if config.current_status != 'ing':
                return None
            msg = f'{str(e)}{str(e.args)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助支持-下载cublasxx.dll,或者切换为openai模型 ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model'
            raise Exception(f'{msg}')
        if config.current_status != 'ing':
            return None
        if not raw_subtitles or len(raw_subtitles) < 1:            
            raise Exception(self.noextname + config.transobj['recogn result is empty'].replace('{lang}', config.params['source_language']))
        self.save_srt_target(raw_subtitles, self.targetdir_source_sub)

    # 翻译字幕
    def trans(self):
        # 如果存在字幕，并且存在目标语言字幕，则前台直接使用该字幕替换
        if self.source_mp4 and os.path.exists(self.targetdir_target_sub) and os.path.getsize(
                self.targetdir_target_sub) > 0:
            # 通知前端替换字幕
            with open(self.targetdir_target_sub, 'r', encoding="utf-8",errors="ignore") as f:
                set_process(f.read().strip(), 'replace_subtitle')
        # 是否需要翻译，不是 tiqu_no/hebing，存在识别后字幕并且不存在目标语言字幕，并且原语言和目标语言不同，则需要翻译
        if self.app_mode in ['tiqu_no', 'hebing'] or \
                os.path.exists(self.targetdir_target_sub) or \
                not os.path.exists(self.targetdir_source_sub) or \
                config.params['target_language'] == '-' or \
                config.params['target_language'] == config.params['source_language']:
            return True

        # 等待编辑原字幕后翻译,允许修改字幕
        set_process(transobj["xiugaiyuanyuyan"], 'edit_subtitle')
        config.task_countdown = config.settings['countdown_sec']
        while config.task_countdown > 0:
            if config.current_status!='ing':
                return False
            if config.task_countdown <= config.settings['countdown_sec'] and config.task_countdown >= 0:
                set_process(f"{config.task_countdown} {transobj['jimiaohoufanyi']}", 'show_djs')
            time.sleep(1)
            config.task_countdown -= 1
        # 禁止修改字幕
        set_process('', 'timeout_djs')
        time.sleep(2)
        # 如果不存在原字幕，或已存在目标语言字幕则跳过，比如使用已有字幕，无需翻译时
        if not os.path.exists(self.targetdir_source_sub) or os.path.exists(self.targetdir_target_sub):
            return True
        # 测试翻译
        switch_trans = ""
        if config.params['translate_type'].lower() == GOOGLE_NAME.lower():
            set_process(config.transobj['test google'])
            if not self.testgoogle():
                raise Exception('无法连接Google,请填写有效代理地址，如果无代理，请查看菜单栏-帮助支持-无代理使用Google翻译')

        set_process(transobj['starttrans'] + switch_trans)
        # 开始翻译,从目标文件夹读取原始字幕
        rawsrt = get_subtitle_from_srt(self.targetdir_source_sub, is_file=True)
        if not rawsrt or len(rawsrt) < 1:
            raise Exception(f"[error]：Subtitles is empty,cannot translate")
        # 开始翻译，禁止修改字幕

        target_srt = run_trans(translate_type=config.params['translate_type'], text_list=rawsrt,
                               target_language_name=config.params['target_language'], set_p=True, inst=self,
                               source_code=self.source_language_code)
        self.save_srt_target(target_srt, self.targetdir_target_sub)

    # 测试google是否可用
    def testgoogle(self):
        text = "你好"
        url = f"https://translate.google.com/m?sl=auto&tl=en&hl=en&q={urllib.parse.quote(text)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        serv = tools.set_proxy()
        proxies = None
        if serv:
            proxies = {
                'http': serv,
                'https': serv
            }
        result = False
        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=300)
            if response.status_code == 200:
                result = True
        except Exception as e:
            print(e)
        return result

    # 配音处理
    def dubbing(self):
        # 不需要配音
        if self.app_mode in ['tiqu', 'tiqu_no', 'hebing'] or \
                config.params['voice_role'] == 'No' or \
                os.path.exists(self.targetdir_target_wav) or \
                not os.path.exists(self.targetdir_target_sub):
            return True
        # 允许修改字幕
        set_process(transobj["xiugaipeiyinzimu"], "edit_subtitle")
        config.task_countdown = config.settings['countdown_sec']
        while config.task_countdown > 0:
            if config.current_status != 'ing':
                return False
            # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
            time.sleep(1)
            # 倒计时中
            config.task_countdown -= 1
            if config.task_countdown <= config.settings['countdown_sec'] and config.task_countdown >= 0:
                set_process(f"{config.task_countdown}{transobj['zidonghebingmiaohou']}", 'show_djs')
        # 禁止修改字幕
        set_process('', 'timeout_djs')
        time.sleep(3)
        try:
            # 禁止修改字幕
            res = self.before_tts()
            if isinstance(res, tuple) and len(res) == 2:
                self.exec_tts(res[0], res[1])
            else:
                raise Exception('no subtitles')
        except Exception as e:
            if str(e)=='stop':
                return False
            # delete_temp(self.noextname)
            raise Myexcept("配音失败:" + str(e))

    # 合并操作
    def hebing(self):
        if self.app_mode in ['tiqu', 'tiqu_no', 'peiyin'] or not self.source_mp4:
            return True
        try:
            self.compos_video()
        except Exception as e:
            if str(e)=='stop':
                return False
            raise Myexcept(f"Compose:" + str(e))

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
        # if total_duration > 0 and (len(merged_audio) > total_duration + 1000):
        #     # 截断前先保存原完整文件
        #     merged_audio.export(f'{self.target_dir}/{self.target_language_code}-nocut.wav', format="wav")
        #     merged_audio = merged_audio[:total_duration]
        # 创建配音后的文件
        try:
            wavfile = self.cache_folder + "/target.wav"
            merged_audio.export(wavfile, format="wav")

            if not self.source_mp4 and self.background_music and os.path.exists(self.background_music):
                cmd = ['-y', '-i', wavfile, '-i', self.background_music, '-filter_complex',
                       "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.targetdir_target_wav]
                runffmpeg(cmd)
            else:
                wav2m4a(wavfile, self.targetdir_target_wav)
        except Exception as e:
            raise Exception(f'[error]merge_audio:{str(e)}')
        return len(merged_audio)

    # 保存字幕文件 到目标文件夹
    def save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        if isinstance(srtstr, list):
            txt = ""
            for it in srtstr:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = startraw.strip().replace('.', ',')
                endraw = endraw.strip().replace('.', ',')
                startraw=format_time(startraw,',')
                endraw=format_time(endraw,',')
                txt += f"{it['line']}\n{startraw} --> {endraw}\n{it['text']}\n\n"
            try:
                with open(file, 'w', encoding="utf-8",errors="ignore") as f:
                    f.write(txt.strip())
                    set_process(txt.strip(), 'replace_subtitle')
            except Exception as e:
                raise Exception(f'Save srt:{str(e)}')
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        total_length = self.video_info['time'] if os.path.exists(self.targetdir_source_wav) else 0
        # 整合一个队列到 exec_tts 执行
        if config.params['voice_role'] == 'No':
            return True
        queue_tts = []
        # 获取字幕
        try:
            print('@@@@0')
            subs = get_subtitle_from_srt(self.targetdir_target_sub)
            if len(subs) < 1:
                raise Exception(f"{os.path.basename(self.targetdir_target_sub)} 字幕格式不正确，请打开查看")
        except Exception as e:
            raise Myexcept(f'[error] tts srt:{str(e)}')
        print('@@@@11')
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
                raise Myexcept('stop')
                # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = config.params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            newrole=voice_role.replace('/','-').replace('\\','/')
            filename = f'{newrole}-{config.params["voice_rate"]}-{config.params["voice_autorate"]}-{it["text"]}'
            md5_hash = hashlib.md5()
            md5_hash.update(f"{filename}".encode('utf-8'))
            # 要保存到的文件
            # clone-voice同时也是音色复制源
            filename = self.cache_folder + "/" + md5_hash.hexdigest() + ".mp3"
            # 如果是clone-voice类型， 需要截取对应片段
            # 如果是clone-voice类型， 需要截取对应片段
            if config.params['tts_type']=='clone-voice':
                if config.params['is_separate'] and not os.path.exists(self.targetdir_source_vocal):
                    raise Exception(f'背景分离出错 {self.targetdir_source_vocal}')
                    # clone 方式文件为wav格式
                
                cut_from_audio(audio_file=self.targetdir_source_vocal if config.params['is_separate'] else self.targetdir_source_wav,ss=it['startraw'],to=it['endraw'],out_file=filename)
         
            queue_tts.append({
                "text": it['text'],
                "role": voice_role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "tts_type": config.params['tts_type'],
                "filename": filename})
        print('@@@@22')
        return (queue_tts, total_length)

    # 将实际配音文件的时长ms 加入
    def _add_time(self,queue_tts):
        for i,it in enumerate(queue_tts):
            if os.path.exists(it['filename']) and os.path.getsize(it['filename'])>0:
                queue_tts[i]['dubb_time']=len(AudioSegment.from_file(it['filename'], format="mp3"))
            else:
                queue_tts[i]['dubb_time']=0
        return queue_tts

    def _ajust_audio(self,queue_tts,is_half=False):
        # 配音加速
        for i,it in enumerate(queue_tts):
            it['speed']=0
            it['add_time']=0
            if it['dubb_time']>0:
                # 有配音文件
                raw_duration=it['end_time']-it['start_time']
                diff=it['dubb_time']-raw_duration
                if raw_duration>0 and diff>0:
                    # 存在原时长，并且新配音大于原时长，才需要加速,计算加速倍数, 原时长不变
                    if not is_half:
                        it['speed']=round(it['dubb_time']/raw_duration,1)
                        it['add_time']=0
                    else:
                        # 加速一半
                        half_diff=int(diff/2)
                        it['speed']=round((raw_duration +half_diff)/raw_duration,1)
                        # 需要更新时间
                        it['add_time']=half_diff
            queue_tts[i]=it
        #再次遍历，调整字幕时间，调整音频长度
        # 每次 start_time 和 end_time 需要添加的长度，为 add_time 之和
        offset=0
        for i,it in enumerate(queue_tts):
            it['start_time']+=offset
            it['end_time']+=offset+it['add_time']
            offset+=it['add_time']
            if it['speed']>0:
                # 调整音频
                tmp_mp3 = os.path.join(self.cache_folder, f'{it["filename"]}-speed.mp3')
                speed_up_mp3(filename=it['filename'], speed=it['speed'], out=tmp_mp3)
                it['filename']=tmp_mp3
            # 更改时间戳
            it['startraw']=ms_to_time_string(ms=it['start_time'])
            it['endraw']=ms_to_time_string(ms=it['end_time'])
            queue_tts[i]=it
        return queue_tts
    # 视频慢速
    def _ajust_video(self,queue_tts):
        pass



    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts, total_length):
        total_length = int(total_length)
        queue_copy = copy.deepcopy(queue_tts)
        if config.current_status != 'ing':
            raise Myexcept('stop')
        if not queue_copy or len(queue_copy) < 1:
            raise Myexcept(f'[error]Queue tts length is 0')
        # 具体配音操作
        try:
            run_tts(queue_tts=queue_tts, language=self.target_language_code, set_p=True, inst=self)
        except Exception as e:
            raise Myexcept(str(e))

        if config.current_status != 'ing':
            raise Myexcept('stop')
        segments = []
        start_times = []
        # 音频最终毫秒数
        audio_length=0
        # 如果设置了视频自动降速 并且有原音频，并且仅仅需要视频自动降速
        if total_length > 0 and config.params['video_autorate'] and not config.params['voice_autorate']:
            set_process('仅视频自动慢速处理')
            offset=0
            for (idx, it) in enumerate(queue_copy):
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                ext = 'mp3'
                # 可能是wav
                if it['filename'].endswith('.wav'):
                    ext = 'wav'
                if not os.path.exists(it['filename']):
                    queue_copy[idx]=it
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format=ext)
                mp3len = len(audio_data)
                wavlen = it['end_time'] - it['start_time']
                diff = mp3len - wavlen
                if diff >0:
                    offset += diff
                    it['end_time'] += diff
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx]=it
                start_times.append(it['start_time'])
                segments.append(audio_data)
            audio_length=self.merge_audio_segments(segments, start_times, total_length)
            self.video_autorate_process(queue_copy,queue_tts, total_length)
        elif not config.params['video_autorate']:
            # 没有视频慢速，仅加速或不处理
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            for (idx, it) in enumerate(queue_copy):
                # 如果有偏移，则添加偏移
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])

                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    queue_copy[idx] = it
                    continue
                ext = 'mp3'
                # 可能是wav
                if it['filename'].endswith('.wav'):
                    ext = 'wav'
                audio_data = AudioSegment.from_file(it['filename'], format=ext)
                mp3len = len(audio_data)
                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']
                if wavlen <= 0:
                    queue_copy[idx] = it
                    continue
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                # 需要加速并根据加速调整字幕时间 原时长时间不变,进行音频加速，如果同时视频慢速，则原时长延长diff的一半
                if config.params["voice_autorate"]:
                    if diff >= 500 and mp3len>=500 and wavlen>0:
                        speed = round(mp3len / wavlen if wavlen > 0 else 1, 2)
                        if config.settings['audio_rate'] > 0 and speed > config.settings['audio_rate']:
                            speed = config.settings['audio_rate']
                        # 新的长度
                        if speed < 50 and speed > 0 and os.path.exists(it['filename']) and os.path.getsize(it['filename']) > 0:
                            tmp_mp3 = os.path.join(self.cache_folder, f'{it["filename"]}.{ext}')
                            speed_up_mp3(filename=it['filename'], speed=speed, out=tmp_mp3)
                            # mp3 降速
                            set_process(f"配音加速 {speed}倍")
                            audio_data = AudioSegment.from_file(tmp_mp3, format=ext)
                            it['end_time']=it['start_time']+int(mp3len/speed)
                        else:
                            offset += diff
                            it['end_time'] += diff
                            logger.error(f'{it["filename"]} 不存在或尺寸为0，加速失败')
                    else:
                        offset += diff
                        it['end_time'] += diff
                elif diff > 0:
                    offset += diff
                    it['end_time'] += diff

                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
            audio_length=self.merge_audio_segments(segments, start_times, total_length)
        elif config.params['video_autorate'] and config.params['voice_autorate']:
            # 2者,先改变配音文件的速度
            offset=0
            start_times=[]
            segments=[]
            for (idx, it) in enumerate(queue_copy):
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    queue_copy[idx]=it
                    continue
                ext = 'mp3'
                # 可能是wav
                if it['filename'].endswith('.wav'):
                    ext = 'wav'
                audio_data = AudioSegment.from_file(it['filename'], format=ext)
                mp3len = len(audio_data)
                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']
                if wavlen <= 0 or mp3len <= 0:
                    queue_copy[idx]=it
                    continue
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                # 如果设置了 音频自动加速 and 设置了视频降速,间距分为一半
                if diff >= 500 and mp3len>500:
                    # 需要加速并根据加速调整字幕时间 原时长时间不变,进行音频加速，如果同时视频慢速，则原时长延长diff的一半
                    diff2=int(diff/2)
                    speed = round((wavlen+diff2) / wavlen if wavlen > 0 else 1, 2)
                    if config.settings['audio_rate'] > 0 and speed > config.settings['audio_rate']:
                        speed = config.settings['audio_rate']
                    # 新的长度
                    if speed < 50 and speed > 0 and os.path.exists(it['filename']) and os.path.getsize(it['filename']) > 0:
                        tmp_mp3 = os.path.join(self.cache_folder, f'{it["filename"]}.{ext}')
                        speed_up_mp3(filename=it['filename'], speed=speed, out=tmp_mp3)
                        shutil.copy2(tmp_mp3, it['filename'])
                        audio_data = AudioSegment.from_file(tmp_mp3, format=ext)
                        # mp3 降速
                        set_process(f"配音加速 {speed}倍")
                        it['end_time']+=diff2
                        offset+=diff2
                    else:
                        offset+=diff
                        logger.error(f'{it["filename"]} 不存在或尺寸为0，加速失败')
                else:
                    offset += diff
                    it['end_time'] += diff
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
            set_process('配音加速处理后，再次进行视频自动慢速处理')
            audio_length=self.merge_audio_segments(segments, start_times, total_length)
            self.video_autorate_process(queue_copy, queue_tts,total_length)

         # 更新字幕
        srt = ""
        for (idx, it) in enumerate(queue_copy):
            srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
        # 字幕保存到目标文件夹
        with open(self.targetdir_target_sub, 'w', encoding="utf-8",errors="ignore") as f:
            f.write(srt.strip())

        # 不是 tiqu tiqu_no peiyin hebing
        if self.app_mode not in ['tiqu','tiqu_no','peiyin','hebing'] and total_length>0 and audio_length>0:
            if total_length+100 < audio_length:
                try:
                    # 对视频末尾定格延长
                    self.novoicemp4_add_time(audio_length - total_length)
                except Exception as e:
                    raise Myexcept(f'[novoicemp4_add_time]{transobj["moweiyanchangshibai"]}:{str(e)}')
        return True

    # 延长 novoice.mp4  duration_ms 毫秒
    def novoicemp4_add_time(self, duration_ms):
        if config.current_status != 'ing':
            return False
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

    # 视频自动降速处理 diff_from 从哪里读取，audio=配音mp3，queue从queue_params=调整后，copy原始
    def video_autorate_process(self, queue_params, queue_raw,source_mp4_total_length):
        if config.current_status != 'ing':
            raise Myexcept('stop')
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Myexcept('not novoice mp4')
        segments = []
        start_times = []
        # 预先创建好的
        # queue_copy = copy.deepcopy(queue_params)
        # 处理过程中不断变化的 novoice_mp4
        novoice_mp4_tmp = f"{self.cache_folder}/novoice_tmp.mp4"

        # 上一个片段的结束时间，用于判断是否需要复制上一个和当前2个片段中间的片段
        last_endtime = 0
        offset = 0
        try:
            # 增加的时间，用于 修改字幕里的开始显示时间和结束时间
            last_index = len(queue_params) - 1
            line_num = 0
            cut_clip = 0
            # 如果字幕开始时间大于0，则先去获取0到字幕开始时间的视频片段
            if queue_raw[0]['start_time'] > 0:
                cut_from_video(ss="00:00:00", to=queue_raw[0]['startraw'], source=self.novoice_mp4, out=novoice_mp4_tmp)
                last_endtime = queue_raw[0]['start_time']
            for (idx, it) in enumerate(queue_params):
                tmppert = f"{self.cache_folder}/tmppert-{idx}.mp4"
                tmppert2 = f"{self.cache_folder}/tmppert2-{idx}.mp4"
                tmppert3 = f"{self.cache_folder}/tmppert3-{idx}.mp4"
                if config.current_status != 'ing':
                    raise Exception('stop')
                jd = round((idx + 1) / (last_index + 1), 1)
                if self.precent < 85:
                    self.precent += jd
                set_process(transobj["videodown.."])
                # 原字幕时间段
                wavlen = queue_raw[idx]['end_time'] - queue_raw[idx]['start_time']
                line_num += 1
                # 开始时间加偏移
                # 该片段配音失败
                # if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    # it['end_time'] = it['start_time'] + wavlen
                    # it['startraw'] = ms_to_time_string(ms=it['start_time'])
                    # it['endraw'] = ms_to_time_string(ms=it['end_time'])
                    # start_times.append(it['start_time'])
                    # segments.append(AudioSegment.silent(duration=wavlen))
                    # queue_params[idx] = it
                    # logger.error(f'配音失败  {it}')
                    # continue
                # ext = "mp3" if it['filename'].endswith('.mp3') else "wav"
                # audio_data = AudioSegment.from_file(it['filename'], format=ext)
                # # 新发音长度
                mp3len = it['end_time']-it['start_time']
                # 先判断，如果 新时长大于旧时长，需要处理
                diff = mp3len - wavlen
                logger.info(f'\n\n{idx=},{mp3len=},{wavlen=},{diff=}')
                # 新时长大于旧时长，视频需要降速播放
                set_process(f"[{idx + 1}/{last_index + 1}] {transobj['shipinjiangsu']} {diff if diff > 0 else 0}ms")
                if diff >= 500 and mp3len >= 500 and wavlen > 0:
                    # 调整视频，新时长/旧时长
                    pts = round(mp3len / wavlen, 2)
                    if config.settings['video_rate'] > 0 and pts > config.settings['video_rate']:
                        pts = config.settings['video_rate']

                    # 当前是第一个需要慢速的
                    if cut_clip == 0:
                        logger.info(f'cut_clip=0, {last_endtime=},{pts=}')
                        # 如果也是视频从0开始的第一个
                        if last_endtime == 0:
                            # 第一个
                            pts = round(mp3len / queue_raw[idx]['end_time'], 2) if queue_raw[idx][
                                                                                        'end_time'] > 0 else 1
                            if config.settings['video_rate'] > 0 and pts > config.settings['video_rate']:
                                pts = config.settings['video_rate']
                            cut_from_video(ss="00:00:00",
                                           to=queue_raw[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=novoice_mp4_tmp)
                            logger.info(f'cut_clip=0,last_endtime==0,{pts=},当前是第一个需要慢速的,也是视频从0开始的第一个')
                        else:
                            logger.info(f'cut_clip=0, {last_endtime=}>0')
                            # 如果当前开始大于上次结束，中间有片段
                            if queue_raw[idx]['start_time'] > last_endtime:
                                logger.info(f'\t start_time > last_endtime  中间有片段')
                                cut_from_video(ss=ms_to_time_string(ms=last_endtime),
                                               to=queue_raw[idx]['startraw'],
                                               source=self.novoice_mp4, out=tmppert)
                                cut_from_video(ss=queue_raw[idx]['startraw'], to=queue_raw[idx]['endraw'],
                                               source=self.novoice_mp4, pts=pts, out=tmppert2)
                                concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert, tmppert2], out=tmppert3)
                                novoice_mp4_tmp = tmppert3
                            else:
                                # 中间无片段
                                logger.info(f'\tstart_time <= last_endtime and 中间无片段')
                                cut_from_video(ss=queue_raw[idx]['startraw'], to=queue_raw[idx]['endraw'],
                                               source=self.novoice_mp4, pts=pts, out=tmppert)
                                concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert], out=tmppert2)
                                novoice_mp4_tmp = tmppert2
                        cut_clip += 1
                    else:
                        logger.info(f'cut_clip>0, {cut_clip=} ,{last_endtime=}')
                        cut_clip += 1
                        # 判断中间是否有
                        pert = queue_raw[idx]['start_time'] - last_endtime
                        if pert > 0:
                            # 和上个片段中间有片段
                            logger.info(f'{pert=}>0,中间有片段')
                            pdlist = [novoice_mp4_tmp]
                            if queue_raw[idx]['start_time'] > queue_raw[idx - 1]['end_time']:
                                cut_from_video(ss=queue_raw[idx - 1]['endraw'], to=queue_raw[idx]['startraw'],
                                               source=self.novoice_mp4, out=tmppert)
                                pdlist.append(tmppert)
                            cut_from_video(ss=queue_raw[idx]['startraw'],
                                           to=queue_raw[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=tmppert2)
                            pdlist.append(tmppert2)
                            concat_multi_mp4(filelist=pdlist, out=tmppert3)
                            novoice_mp4_tmp = tmppert3
                        else:
                            # 和上个片段间中间无片段
                            logger.info(f'pert==0,中间无片段')
                            pdlist = [novoice_mp4_tmp]
                            cut_from_video(ss=queue_raw[idx]['startraw'], to=queue_raw[idx]['endraw'],
                                           source=self.novoice_mp4, pts=pts, out=tmppert)
                            pdlist.append(tmppert)
                            concat_multi_mp4(filelist=pdlist, out=tmppert2)
                            novoice_mp4_tmp = tmppert2
                    last_endtime = queue_raw[idx]['end_time']
                else:
                    # 不需要慢速
                    logger.info(f'diff<=0,不需要降速')
                    if last_endtime == 0:
                        logger.info(f'last_endtime=0,是第一个片段')
                        # 是第一个视频片段
                        cut_from_video(ss="00:00:00.000",
                                       to=queue_raw[idx]['endraw'],
                                       source=self.novoice_mp4, out=novoice_mp4_tmp)
                    else:
                        # 不是第一个
                        logger.info(f'{last_endtime=}>0，不是第一个片段')
                        cut_from_video(ss=ms_to_time_string(ms=last_endtime),
                                       to=queue_raw[idx]['endraw'],
                                       source=self.novoice_mp4, out=tmppert)
                        concat_multi_mp4(filelist=[novoice_mp4_tmp, tmppert], out=tmppert2)
                        novoice_mp4_tmp = tmppert2
                    last_endtime = queue_raw[idx]['end_time']

        except Exception as e:
            if config.current_status != 'ing':
                raise Myexcept(f"{transobj['mansuchucuo']}:" + str(e))
            else:
                return False

        set_process(f"Origin:{source_mp4_total_length=} + offset:{offset} = {source_mp4_total_length + offset}")

        shutil.copy2(novoice_mp4_tmp, self.novoice_mp4)
        # 总长度，单位ms
        total_length = int(get_video_duration(self.novoice_mp4))
        set_process(f"{transobj['xinshipinchangdu']}:{source_mp4_total_length + offset}ms")


    def _back_music(self):
        if config.params['voice_role'] != 'No' and os.path.exists(
                self.targetdir_target_wav) and self.background_music and os.path.exists(self.background_music):
            try:
                # 获取视频长度
                vtime = get_video_info(self.novoice_mp4, video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = get_audio_time(self.background_music)
                # 转为m4a
                if not self.background_music.lower().endswith('.m4a'):
                    tmpm4a = self.cache_folder + f"/background_music-1.m4a"
                    wav2m4a(self.background_music, tmpm4a)
                    self.background_music = tmpm4a
                if atime + 1 < vtime:
                    # 获取延长片段
                    cmd = ['-y', '-i', self.background_music, '-ss', '00:00:00.000', '-t', f'{round(vtime - atime, 1)}',
                           self.cache_folder + "/yanchang.m4a"]
                    runffmpeg(cmd)
                    # 背景音频连接延长片段
                    concat_multi_audio(filelist=[self.background_music, self.cache_folder + "/yanchang.m4a"],
                                       out=self.cache_folder + "/background_music-2.m4a")
                    self.background_music = self.cache_folder + "/background_music-2.m4a"
                # 背景音频降低音量
                runffmpeg(['-y', '-i', self.background_music, "-filter:a", f"volume={config.settings['backaudio_volume']}", '-c:a', 'aac',
                           self.cache_folder + f"/background_music-3.m4a"])
                # 背景音频和配音合并
                cmd = ['-y', '-i', self.cache_folder + f"/background_music-3.m4a", '-i', self.targetdir_target_wav,
                       '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.cache_folder + f"/lastend.m4a"]
                runffmpeg(cmd)
                self.targetdir_target_wav = self.cache_folder + f"/lastend.m4a"
            except Exception as e:
                logger.error(f'添加背景音乐失败:{str(e)}')

    def _separate(self):
        if config.params['is_separate'] and os.path.exists(self.targetdir_target_wav):
            try:
                # 原始背景音乐 wav,和配音后的文件m4a合并
                # 获取视频长度
                vtime = get_video_info(self.novoice_mp4, video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = get_audio_time(self.targetdir_source_instrument)
                if atime + 1 < vtime:
                    # 延长背景音
                    cmd = ['-y', '-i', self.targetdir_source_instrument, '-ss', '00:00:00.000', '-t',
                           f'{round(vtime - atime, 1)}', self.cache_folder + "/yanchang.m4a"]
                    runffmpeg(cmd)
                    # 背景音连接延长片段
                    concat_multi_audio(filelist=[self.targetdir_source_instrument, self.cache_folder + "/yanchang.m4a"],
                                       out=self.cache_folder + f"/instrument-2.m4a")

                    self.targetdir_source_instrument = self.cache_folder + f"/instrument-2.m4a"
                # 背景音合并配音
                backandvocal(self.targetdir_source_instrument, self.targetdir_target_wav)
            except Exception as e:
                logger.error('合并原始背景失败' + config.transobj['Error merging background and dubbing'] + str(e))

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def compos_video(self):
        if config.current_status != 'ing':
            raise Myexcept('stop')
        if self.app_mode in ['tiqu', 'tiqu_no', 'peiyin']:
            return True
        # 判断novoice_mp4是否完成
        if not is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Myexcept("not novoice mp4")
        # 需要配音,选择了角色，并且不是 提取模式 合并模式
        if self.app_mode == 'hebing':
            config.params['voice_role'] = 'No'
        if config.params['voice_role'] != 'No':
            if not os.path.exists(self.targetdir_target_wav) or os.path.getsize(self.targetdir_target_wav)<1:
                raise Myexcept(f"{config.transobj['Dubbing']}{config.transobj['anerror']}:{self.targetdir_target_wav}")

        # 需要字幕
        if config.params['subtitle_type'] > 0 and not os.path.exists(self.targetdir_target_sub):
            raise Myexcept(f"No subtitles file: {self.targetdir_target_sub}")
        if self.precent < 85:
            self.precent = 85
        fontsize=""
        #软双字幕时，同步时间后的原语言字幕
        soft_subtitle_raw=None
        soft_source_subtitle_lang=None
        if config.params['subtitle_type'] in [1,3]:
            # 硬字幕 重新整理字幕，换行
            try:
                subs = get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                raise Myexcept(f'Subtitles error:{str(e)}')

            # 双字幕并且合并模式
            source_sub=[]
            if config.params['subtitle_type']==3 and self.app_mode != 'hebing' and self.source_language_code != self.target_language_code:
                try:
                    source_sub = get_subtitle_from_srt(self.targetdir_source_sub)
                except Exception as e:
                    raise Myexcept(f'Source Subtitles error:{str(e)}')
            maxlen = config.settings['cjk_len'] if self.target_language_code[:2] in ["zh", "ja", "jp", "ko"] else config.settings['other_len']
            maxlen_source = config.settings['cjk_len'] if self.source_language_code[:2] in ["zh", "ja", "jp", "ko"] else config.settings['other_len']
            subtitles = ""
            source_length=len(source_sub)
            for i,it in enumerate(subs):
                it['text'] = textwrap.fill(it['text'], maxlen)
                subtitles += f"{it['line']}\n{it['time']}\n{it['text'].strip()}"
                if source_length>0 and i<source_length:
                    subtitles+="\n"+textwrap.fill(source_sub[i]['text'],maxlen_source).strip()
                subtitles+="\n\n"
            with open(self.targetdir_target_sub, 'w', encoding="utf-8",errors="ignore") as f:
                f.write(subtitles.strip())
            shutil.copy2(self.targetdir_target_sub, config.rootdir + "/tmp.srt")


            os.chdir(config.rootdir)
            hard_srt = "tmp.srt"
            fontsize=f":force_style=Fontsize={config.settings['fontsize']}" if config.settings['fontsize']>0 else ""
        elif config.params['subtitle_type'] ==4 and self.app_mode != 'hebing' and self.source_language_code != self.target_language_code:
            soft_source_subtitle_lang=get_subtitle_code(show_target=config.params['source_language'])
            soft_subtitle_raw=self.targetdir_source_sub
            if config.params['voice_role'] != 'No':
                soft_subtitle_raw=self.cache_folder+"/soft_source_subtitle.srt"
                try:
                    # 取出目标字幕的时间，将原语言字幕的时间替换
                    target_subs = get_subtitle_from_srt(self.targetdir_target_sub)
                    source_subs = get_subtitle_from_srt(self.targetdir_source_sub)
                    text=""
                    for i,it in enumerate(target_subs):
                        if i < len(source_subs):
                            text+= f"{source_subs[i]['line']}\n{it['time']}\n{source_subs[i]['text']}\n\n"
                    with open(soft_subtitle_raw, 'w', encoding="utf-8",errors="ignore") as f:
                        f.write(text.strip())
                except Exception as e:
                    raise Myexcept(f'Subtitles error:{str(e)}')

        if self.precent < 90:
            self.precent = 90
        # 有字幕有配音
        if self.app_mode !='hebing':
            self._back_music()
            self._separate()
        if config.params['only_video']:
            self.targetdir_mp4 = config.params['target_dir'] + f"/{self.noextname}.mp4"

        try:
            #有配音有字幕
            if config.params['voice_role'] != 'No' and config.params['subtitle_type'] > 0:
                if config.params['subtitle_type'] in [1,3]:
                    set_process(transobj['peiyin-yingzimu'])
                    # 需要配音+硬字幕
                    runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        '-filter_complex',
                        "[1:a]apad",
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        "-vf",
                        f"subtitles={hard_srt}{fontsize}",
                        "-shortest",
                        os.path.normpath(self.targetdir_mp4),
                    ], de_format="nv12")
                else:
                    set_process(transobj['peiyin-ruanzimu'])
                    # 配音+软字幕
                    runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(self.novoice_mp4),
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-i",
                        os.path.normpath(self.targetdir_target_sub),
                        '-filter_complex', "[1:a]apad",
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={self.subtitle_language}",
                        "-shortest",
                        os.path.normpath(self.targetdir_mp4)
                    ])
                    if soft_source_subtitle_lang and soft_subtitle_raw:
                        runffmpeg([
                            "-y",
                            "-i",
                            os.path.normpath(self.novoice_mp4),
                            "-i",
                            os.path.normpath(self.targetdir_target_wav),
                            "-i",
                            os.path.normpath(self.targetdir_target_sub),
                            "-i",
                            os.path.normpath(soft_subtitle_raw),
                            '-map',
                            '0',
                            '-map',
                            '1',
                            '-map',
                            '2',
                            '-map',
                            '3',
                            '-filter_complex',
                            "[1:a]apad",
                            "-c:v",
                            "libx264",
                            "-c:a",
                            "aac",
                            "-c:s",
                            "mov_text",
                            "-metadata:s:s:0",
                            f"language={self.subtitle_language}",
                            "-metadata:s:s:1",
                            f"language={soft_source_subtitle_lang}",
                            "-shortest",
                            os.path.normpath(self.targetdir_mp4)
                        ])
                        print(f"{self.subtitle_language=}")
                        print(f"{soft_source_subtitle_lang=}")
            elif config.params['voice_role'] != 'No':
                # 有配音无字幕
                set_process(transobj['onlypeiyin'])
                rs = runffmpeg([
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4),
                    "-i",
                    os.path.normpath(self.targetdir_target_wav),
                    '-filter_complex', "[1:a]apad",
                    "-c:v",
                    "libx264",
                    # "libx264",
                    "-c:a",
                    "aac",
                    # "pcm_s16le",
                    "-shortest",
                    os.path.normpath(self.targetdir_mp4)
                ])
            # 有字幕无配音  原始 wav合并
            elif config.params['subtitle_type'] in [1,3]:
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
                    cmd.append('aac')
                cmd += [
                    "-vf",
                    f"subtitles={hard_srt}{fontsize}",
                    os.path.normpath(self.targetdir_mp4),
                ]
                runffmpeg(cmd, de_format="nv12")
            elif config.params['subtitle_type'] in [2,4]:
                # 软字幕无配音
                set_process(transobj['onlyruanzimu'])
                #原视频
                stream_num=1
                cmd = [
                    "-y",
                    "-i",
                    os.path.normpath(self.novoice_mp4)
                ]
                #原配音流
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append("-i")
                    cmd.append(os.path.normpath(self.targetdir_source_wav))
                    stream_num+=1
                #目标字幕流
                cmd += [
                    "-i",
                    os.path.normpath(self.targetdir_target_sub),
                ]
                stream_num+=1
                #原语言字幕流
                if soft_subtitle_raw and soft_source_subtitle_lang:
                    cmd.append("-i")
                    cmd.append(os.path.normpath(soft_subtitle_raw))
                    stream_num+=1

                for i in range(stream_num):
                    cmd.append('-map')
                    cmd.append(f'{i}')

                cmd+=[
                    "-c:v",
                    "libx264"
                ]
                if os.path.exists(self.targetdir_source_wav):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += ["-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={self.subtitle_language}",
                ]
                if soft_subtitle_raw and soft_source_subtitle_lang:
                    cmd+=[
                        "-metadata:s:s:1",
                        f"language={soft_source_subtitle_lang}",
                    ]
                cmd.append(os.path.normpath(self.targetdir_mp4))
                runffmpeg(cmd)
        except Exception as e:
            raise Myexcept(f'compose join srt+video+audio:{str(e)}')
        if self.precent < 100:
            self.precent = 99
        try:
            if os.path.exists(config.rootdir + "/tmp.srt"):
                os.unlink(config.rootdir + "/tmp.srt")
            if not config.params['only_video']:
                with open(os.path.join(self.target_dir, f'{"readme" if config.defaulelang != "zh" else "文件说明"}.txt'),'w', encoding="utf-8",errors="ignore") as f:
                    f.write(f"""以下是可能生成的全部文件, 根据执行时配置的选项不同, 某些文件可能不会生成, 之所以生成这些文件和素材，是为了方便有需要的用户, 进一步使用其他软件进行处理, 而不必再进行语音导出、音视频分离、字幕识别等重复工作


{os.path.basename(self.targetdir_mp4)} = 最终完成的目标视频文件
{self.source_language_code}.m4a|.wav = 原始视频中的音频文件(包含所有背景音和人声)
{self.target_language_code}.m4a = 配音后的音频文件(若选择了保留背景音乐则已混入)
{self.source_language_code}.srt = 原始视频中根据声音识别出的字幕文件
{self.target_language_code}.srt = 翻译为目标语言后字幕文件
vocal.wav = 原始视频中分离出的人声音频文件
instrument.wav = 原始视频中分离出的背景音乐音频文件


如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎各位小额赞助，有了一定资金支持，我将能够持续投入更多时间和精力
捐助地址：https://github.com/jianchang512/pyvideotrans/issues/80

====

Here are the descriptions of all possible files that might exist. Depending on the configuration options when executing, some files may not be generated.

{os.path.basename(self.targetdir_mp4)} = The final completed target video file
{self.source_language_code}.m4a|.wav = The audio file in the original video (containing all sounds)
{self.target_language_code}.m4a = The dubbed audio file (if you choose to keep the background music, it is already mixed in)
{self.source_language_code}.srt = Subtitles recognized in the original video
{self.target_language_code}.srt = Subtitles translated into the target language
vocal.wav = The vocal audio file separated from the original video
instrument.wav = The background music audio file separated from the original video


If you feel that this project is valuable to you and hope that it can be maintained consistently, we welcome small sponsorships. With some financial support, I will be able to continue to invest more time and energy
Donation address: https://ko-fi.com/jianchang512


====

Github: https://github.com/jianchang512/pyvideotrans
Docs: https://pyvideotrans.com

                """)
            if os.path.exists(self.targetdir_source_regcon):
                os.unlink(self.targetdir_source_regcon)
            shutil.rmtree(self.cache_folder, True)
        except:
            pass
        self.precent = 100
        if config.params['only_video']:
            # 保留软字幕
            if config.params['subtitle_type'] == 2 and os.path.exists(self.targetdir_target_sub):
                shutil.copy2(self.targetdir_target_sub,config.params['target_dir'] + f"/{self.noextname}-{self.target_language_code}.srt")

            if config.params['subtitle_type'] == 4 and os.path.exists(self.targetdir_source_sub):
                shutil.copy2(self.targetdir_source_sub,config.params['target_dir'] + f"/{self.noextname}-{self.source_language_code}.srt")
            shutil.rmtree(self.target_dir, True)
        return True
