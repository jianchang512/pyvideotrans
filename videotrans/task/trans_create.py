import copy
import datetime
import hashlib
import math
import os
import re
import shutil
import textwrap
import threading
import time
from pydub import AudioSegment
from videotrans.configure import config
from videotrans.recognition import run as run_recogn
from videotrans.tts import run as run_tts
from videotrans.translator import run as run_trans, get_audio_code, get_subtitle_code
from videotrans.util import tools
from pathlib import Path

class TransCreate():
    '''

    obj={
        "raw_name":name,
        # 原始视频所在原始目录
        "raw_dirname":raw_dirname,
        # 原始视频原始名字带后缀
        "raw_basename":raw_basename,
        # 原始视频名字不带后缀
        "raw_noextname":raw_noextname,
        # 原始后缀不带 .
        "raw_ext":ext[1:],
        # 处理后 移动后符合规范的目录名
        "dirname":"",
        # 符合规范的基本名带后缀
        "basename":"",
        # 符合规范的不带后缀
        "noextname":"",
        # 扩展名
        "ext":ext[1:],
        # 最终存放目标位置，直接存到这里
        "output": f'{out}/{raw_noextname}' if out else f'{raw_dirname}/{raw_noextname}',
        "unid":"",
        "source_mp4":name
    }

    '''

    def __init__(self, config_params=None, obj=None):
        self.raw_basename = obj['raw_basename'] if obj else " srt "
        self.config_params = config_params
        self.app_mode = config_params['app_mode']
        # 原始视频信息
        self.video_info = None
        self.obj = obj
        self.output = obj['output'] if obj else ""

        self.h264 = True

        # 识别是否结束
        self.regcon_end = False
        # 翻译是否结束
        self.trans_end = False
        # 配音是否结束
        self.dubb_end = False
        # 合并是否结束
        self.compose_end = False
        # 进度
        self.precent = 0
        self.background_music = None
        self.detect_language = None
        self.subtitle_language = None

        # 原始视频
        self.source_mp4 = self.obj['source_mp4'] if self.obj else ""
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

        # 存在添加的背景音乐
        if self.config_params['back_audio'] and Path(self.config_params['back_audio']).exists():
            self.background_music = self.config_params['back_audio']

        # 如果是字幕创建配音模式
        if self.app_mode == 'peiyin':
            self.noextname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.precent = 40
            self.target_dir = self.config_params['target_dir'] if self.config_params['target_dir']  else f"{config.homedir}/only_dubbing"
            self.btnkey = "srt2wav"
        else:
            # 不带后缀的视频名字
            self.noextname = self.obj['noextname']
            # 进度按钮
            self.btnkey = self.obj['unid']
            # 临时作为目标目录，最后再根据条件移动
            self.target_dir = self.obj['linshi_output']
            # 如果不是仅提取，则获取视频信息
            if self.app_mode not in ['tiqu', 'peiyin']:
                # 获取视频信息
                try:
                    self.video_info = tools.get_video_info(self.source_mp4)
                except Exception as e:
                    raise Exception(f"{config.transobj['get video_info error']}:{str(e)}")

                if not self.video_info:
                    raise Exception(config.transobj['get video_info error'])
                if self.video_info['video_codec_name'] != 'h264' or self.obj['ext'].lower() != 'mp4':
                    self.h264 = False

        # 临时文件夹
        self.cache_folder = f"{config.rootdir}/tmp/{self.noextname}"

        # 创建文件夹
        Path(self.target_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        # 获取原语言代码和目标语言代码
        if "mode" in self.config_params and self.config_params['mode'] == "cli":
            self.source_language_code = self.config_params['source_language']
            self.target_language_code = self.config_params['target_language']
        else:
            # 仅作为文件名标识
            self.source_language_code, self.target_language_code = config.rev_langlist[
                                                                       self.config_params['source_language']] if \
                                                                       self.config_params[
                                                                           'source_language'] != '-' else '-', \
                                                                   config.rev_langlist[
                                                                       self.config_params['target_language']] if \
                                                                       self.config_params[
                                                                           'target_language'] != '-' else '-'

        # 检测字幕原始语言
        if self.config_params['source_language'] != '-':
            self.detect_language = get_audio_code(show_source=self.config_params['source_language'])
        if self.config_params['target_language'] != '-':
            self.subtitle_language = get_subtitle_code(show_target=self.config_params['target_language'])

        self.novoice_mp4 = f"{self.target_dir}/novoice.mp4"
        self.targetdir_source_sub = f"{self.target_dir}/{self.source_language_code}.srt"
        self.targetdir_target_sub = f"{self.target_dir}/{self.target_language_code}.srt"
        # 原wav
        self.targetdir_source_wav = f"{self.target_dir}/{self.source_language_code}.m4a"
        # 配音后的音频文件
        self.targetdir_target_wav = f"{self.target_dir}/{self.target_language_code}.m4a"
        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.config_params['voice_role'] != 'No' and self.source_language_code == self.target_language_code:
            self.targetdir_target_wav = f"{self.target_dir}/{self.target_language_code}-dubbing.m4a"
        # 最终的mp4视频
        self.targetdir_mp4 = f"{self.target_dir}/{self.noextname}.mp4"

        # 分离出的原始音频文件
        if self.config_params['is_separate']:
            # 背景音乐
            self.targetdir_source_instrument = f"{self.target_dir}/instrument.wav"
            # 转为8k采样率，降低文件
            self.targetdir_source_vocal = f"{self.target_dir}/vocal.wav"
        else:
            self.targetdir_source_vocal = None
            self.targetdir_source_instrument = None

        # 作为识别音频
        self.shibie_audio = f"{self.target_dir}/shibie.wav"

        # 如果存在字幕，则视为目标字幕，直接生成，不再识别和翻译
        if "subtitles" in self.config_params and self.config_params['subtitles'].strip():
            sub_file = self.targetdir_target_sub
            if self.config_params['source_language'] != self.config_params['target_language'] and self.config_params[
                'source_language'] != '-' and self.config_params['target_language'] != '-':
                # 原始和目标语言都存在，并且不相等，需要翻译，作为待翻译字幕
                sub_file = self.targetdir_source_sub
            with open(sub_file, 'w', encoding="utf-8", errors="ignore") as f:
                f.write(self.config_params['subtitles'].strip())

        # 如何名字不合规迁移了，并且存在原语言或目标语言字幕
        if self.app_mode!='srt2wav' and self.obj['output'] != self.obj['linshi_output']:
            raw_source_srt=self.obj['output']+f'/{self.source_language_code}.srt'
            
            if Path(raw_source_srt).is_file():
                shutil.copy2(raw_source_srt,self.targetdir_source_sub)

            raw_target_srt=self.obj['output']+f'/{self.target_language_code}.srt'
            if Path(raw_target_srt).is_file():
                shutil.copy2(raw_target_srt,self.targetdir_target_sub)


    # 启动执行入口
    def prepare(self):
        # 获取set.ini配置
        config.settings = config.parse_init()
        if self.config_params['tts_type'] == 'clone-voice':
            tools.set_process(config.transobj['test clone voice'], btnkey=self.btnkey)
            try:
                tools.get_clone_role(True)
            except Exception as e:
                raise Exception(str(e))
        self.precent += 3
        # 禁止修改字幕
        tools.set_process("", "disabled_edit", btnkey=self.btnkey)
        self._split_wav_novicemp4()

    # 是否需要识别，识别是否完成
    def is_recogn(self):
        shound = True
        if self.app_mode in ['hebing', 'peiyin']:
            shound = False
        return shound, self.regcon_end

    # 是否需要翻译，翻译是否完成
    def is_trans(self):
        shound = True
        if self.app_mode in ['hebing'] or \
                self.config_params['target_language'] == '-' or \
                self.config_params['target_language'] == self.config_params['source_language']:
            shound = False
        return shound, self.trans_end

    # 是否需要配音，是否完成
    def is_dubb(self):
        shound = True
        if self.app_mode in ['tiqu', 'hebing'] or \
                self.config_params['voice_role'] == 'No':
            shound = False
        return shound, self.dubb_end

    # 是否需要合并，合并是否完成
    def is_compose(self):
        shound = True
        if self.app_mode in ['tiqu', 'peiyin']:
            shound = False
        if self.config_params['voice_role'] == 'No' and self.config_params['subtitle_type'] == 0:
            shound = False
        return shound, self.compose_end

    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def move_at_end(self):
        output = self.obj['output']

        # 需要移动
        if self.obj['output'] != self.obj['linshi_output']:
            target_mp4=Path(self.targetdir_mp4)
            if target_mp4.exists():
                target_mp4.rename(Path(self.obj['linshi_output'] + f'/{self.obj["raw_noextname"]}.mp4'))
            shutil.copytree(self.obj['linshi_output'], self.obj['output'], dirs_exist_ok=True)

        # 仅保存视频
        if self.config_params['only_video']:
            # 硬字幕，移动到上一级
            output=Path(self.obj["output"])
            for it in output.iterdir():
                # 软字幕时也需要保存字幕
                ext = it.suffix.lower()
                if int(self.config_params['subtitle_type']) in [2, 4]:
                    if ext not in ['.mp4', '.srt']:
                        it.unlink(missing_ok=True)
                elif int(self.config_params['subtitle_type']) in [1, 3]:
                    # 硬字幕 移动视频到上一级
                    if ext != '.mp4':
                        it.unlink(missing_ok=True)
                    else:
                        try:
                            it.rename(it.parent/"../"/f'{it.name}')
                        except Exception:
                            pass
            # 硬字幕删除文件夹
            if int(self.config_params['subtitle_type']) in [1, 3]:
                shutil.rmtree(self.obj["output"], ignore_errors=True)
        self.precent = 100
        self.output = output
        shutil.rmtree(self.cache_folder, ignore_errors=True)
        # 批量不允许编辑字幕
        if not self.config_params['is_batch']:
            tools.set_process('', 'allow_edit', btnkey=self.btnkey)
        tools.set_process(f"{output}##{self.obj['raw_basename']}",
                          'succeed',
                          btnkey=self.btnkey
                          )

    # 分离音频 和 novoice.mp4
    def _split_wav_novicemp4(self):
        # 存在视频 不是peiyin
        if self.app_mode == 'peiyin':
            return True

        # 合并字幕时不分离，直接复制
        if self.app_mode == 'hebing':
            shutil.copy2(self.source_mp4, self.novoice_mp4)
            config.queue_novice[self.noextname] = 'end'
            return True

        # 不是 提取字幕时，需要分离出视频
        if self.app_mode not in ['tiqu']:
            threading.Thread(target=tools.split_novoice_byraw,
                             args=(self.source_mp4, self.novoice_mp4, self.noextname,
                                   "copy" if self.h264 else "libx264")).start()
        else:
            config.queue_novice[self.noextname] = 'end'

        # 添加是否保留背景选项
        self.precent += 3
        if self.config_params['is_separate'] and not Path(self.targetdir_source_vocal).exists():
            # 背景分离音
            try:
                tools.set_process(config.transobj['Separating background music'], btnkey=self.btnkey)
                tools.split_audio_byraw(self.source_mp4, self.targetdir_source_wav, True)
            except Exception as e:
                pass
            finally:
                if not Path(self.targetdir_source_vocal).exists():
                    self.targetdir_source_instrument = None
                    self.targetdir_source_vocal = None
                    self.config_params['is_separate'] = False
                else:
                    # 分离成功后转为8k待识别音频
                    tools.conver_to_8k(self.targetdir_source_vocal, self.shibie_audio)
        # 不分离，或分离失败
        if not self.config_params['is_separate']:
            try:
                tools.split_audio_byraw(self.source_mp4, self.targetdir_source_wav)
                tools.conver_to_8k(self.targetdir_source_wav, self.shibie_audio)
            except Exception as e:
                raise Exception(
                    '从视频中提取声音失败，请检查视频中是否含有音轨，或该视频是否存在编码问题' if config.defaulelang == 'zh' else 'Failed to extract sound from video, please check if the video contains an audio track or if there is an encoding problem with that video')
        return True

    # 开始识别出字幕
    def recogn(self):
        self.precent += 3
        tools.set_process(config.transobj["kaishishibie"], btnkey=self.btnkey)
        # 如果不存在视频，或存在已识别过的，或存在目标语言字幕 或合并模式，不需要识别
        if self.app_mode in ['hebing', 'peiyin']:
            self.regcon_end = True
            return True
        print(f'{self.targetdir_source_sub=}')
        if Path(self.targetdir_source_sub).exists():
            self.regcon_end = True
            return True
        #####识别阶段 存在已识别后的字幕，并且不存在目标语言字幕，则更新替换界面字幕
        if Path(self.targetdir_target_sub).exists():
            # 通知前端替换字幕
            with open(self.targetdir_source_sub, 'r', encoding="utf-8", errors="ignore") as f:
                tools.set_process(f.read().strip(), 'replace_subtitle', btnkey=self.btnkey)
            self.regcon_end = True
            return True

        # 分离未完成，需等待
        while not Path(self.targetdir_source_wav).exists():
            tools.set_process(config.transobj["running"], btnkey=self.btnkey)
            time.sleep(1)
        print(f'{self.targetdir_target_sub=}')
        # 识别为字幕
        try:
            self.precent += 5
            raw_subtitles = run_recogn(
                # faster-whisper openai-whisper googlespeech
                model_type=self.config_params['model_type'],
                # 整体 预先 均等
                type=self.config_params['whisper_type'],
                # 模型名
                model_name=self.config_params['whisper_model'],
                # 识别音频
                audio_file=self.shibie_audio,
                detect_language=self.detect_language,
                cache_folder=self.cache_folder,
                is_cuda=self.config_params['cuda'],
                inst=self)
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model'
            self.regcon_end = True
            raise Exception(f'{msg}')

        if not raw_subtitles or len(raw_subtitles) < 1:
            self.regcon_end = True
            raise Exception(self.obj['raw_basename'] + config.transobj['recogn result is empty'].replace('{lang}',
                                                                                                         self.config_params[
                                                                                                             'source_language']))
        self._save_srt_target(raw_subtitles, self.targetdir_source_sub)
        # 删除识别音频
        try:
            os.unlink(self.shibie_audio)
        except Exception:
            pass
        self.regcon_end = True
        return True

    # 翻译字幕
    def trans(self):
        self.precent += 3
        # 是否需要翻译，不是 hebing，存在识别后字幕并且不存在目标语言字幕，并且原语言和目标语言不同，则需要翻译
        if self.app_mode in ['hebing'] or \
                self.config_params['target_language'] == '-' or \
                self.config_params['target_language'] == self.config_params['source_language'] or not Path(self.targetdir_source_sub).exists():
            self.trans_end = True
            return True

        config.task_countdown = 0 if self.app_mode == 'biaozhun_jd' else config.settings['countdown_sec']

        # 如果存在目标语言字幕，前台直接使用该字幕替换
        if Path(self.targetdir_target_sub).exists():
            # 通知前端替换字幕
            with open(self.targetdir_target_sub, 'r', encoding="utf-8", errors="ignore") as f:
                tools.set_process(f.read().strip(), 'replace_subtitle', btnkey=self.btnkey)
                self.trans_end = True
                return True

        # 批量不允许修改字幕
        if not self.config_params['is_batch']:
            # 等待编辑原字幕后翻译,允许修改字幕
            tools.set_process(config.transobj["xiugaiyuanyuyan"], 'edit_subtitle', btnkey=self.btnkey)
            while config.task_countdown > 0:
                config.task_countdown -= 1
                if config.task_countdown <= config.settings['countdown_sec']:
                    tools.set_process(f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}", 'show_djs',
                                      btnkey=self.btnkey)
                time.sleep(1)

            # 禁止修改字幕
            tools.set_process('translate_start', 'timeout_djs', btnkey=self.btnkey)
            time.sleep(2)
        # 如果不存在原字幕，或已存在目标语言字幕则跳过，比如使用已有字幕，无需翻译时
        if not Path(self.targetdir_source_sub).exists() or Path(self.targetdir_target_sub).exists():
            if self.app_mode == 'tiqu':
                self.compose_end = True
            self.trans_end = True
            return True
        tools.set_process(config.transobj['starttrans'], btnkey=self.btnkey)
        # 开始翻译,从目标文件夹读取原始字幕
        rawsrt = tools.get_subtitle_from_srt(self.targetdir_source_sub, is_file=True)
        if not rawsrt or len(rawsrt) < 1:
            self.trans_end = True
            raise Exception(f'{self.obj["raw_basename"]}' + config.transobj['No subtitles file'])
        # 开始翻译，禁止修改字幕
        try:
            target_srt = run_trans(
                translate_type=self.config_params['translate_type'],
                text_list=rawsrt,
                target_language_name=self.config_params['target_language'],
                set_p=True,
                inst=self,
                source_code=self.source_language_code)
        except Exception as e:
            raise Exception(e)
        self._save_srt_target(target_srt, self.targetdir_target_sub)
        if self.app_mode == 'tiqu':
            self.compose_end = True
        self.trans_end = True
        return True

    # 配音处理
    def dubbing(self):
        self.precent += 3
        config.task_countdown = 0 if self.app_mode == 'biaozhun_jd' else config.settings['countdown_sec']

        # 不需要配音
        if self.app_mode in ['tiqu', 'hebing'] or \
                self.config_params['voice_role'] == 'No' or \
                not Path(self.targetdir_target_sub).exists():
            self.dubb_end = True
            return True
        if Path(self.targetdir_target_wav).exists():
            if self.app_mode == 'peiyin':
                self.compose_end = True
            self.dubb_end = True
            return True
        # 允许修改字幕
        if not self.config_params['is_batch']:
            tools.set_process(config.transobj["xiugaipeiyinzimu"], "edit_subtitle", btnkey=self.btnkey)
            while config.task_countdown > 0:
                # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                time.sleep(1)
                # 倒计时中
                config.task_countdown -= 1
                if config.task_countdown <= config.settings['countdown_sec']:
                    tools.set_process(f"{config.task_countdown}{config.transobj['zidonghebingmiaohou']}", 'show_djs',
                                      btnkey=self.btnkey)
            # 禁止修改字幕
            tools.set_process('dubbing_start', 'timeout_djs', btnkey=self.btnkey)
        tools.set_process(config.transobj['kaishipeiyin'], btnkey=self.btnkey)
        time.sleep(3)
        try:
            self._exec_tts(self._before_tts())
        except Exception as e:
            self.dubb_end = True
            raise Exception(e)
        if self.app_mode == 'peiyin':
            self.compose_end = True
        self.dubb_end = True
        return True

    # 合并操作
    def hebing(self):
        self.precent += 3
        # 视频 音频 字幕 合并
        if self.app_mode in ['tiqu', 'peiyin']:
            self.compose_end = True
            return True
        try:
            self._compos_video()
        except Exception as e:
            self.compose_end = True
            raise Exception(e)
        self.compose_end = True
        self.precent = 100
        return True

    def _merge_audio_segments(self, *, queue_tts=None, video_time=0):
        merged_audio = AudioSegment.empty()
        # start is not 0
        if queue_tts[0]['start_time'] > 0:
            silence_duration = queue_tts[0]['start_time']
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence
        # join
        offset = 0
        for i, it in enumerate(queue_tts):
            it['raw_duration'] = it['end_time'] - it['start_time']
            if it['raw_duration'] == 0:
                continue
            if not Path(it['filename']).exists():
                merged_audio += AudioSegment.silent(duration=it['raw_duration'])
                continue
            segment = AudioSegment.from_file(it['filename'], format=it['filename'].split('.')[-1])
            the_dur = len(segment)
            # 字幕可用时间
            raw_dur = it['raw_duration']
            it['start_time'] += offset
            it['end_time'] += offset

            diff = the_dur - raw_dur
            # 配音大于字幕时长，后延，延长时间
            if diff > 0:
                it['end_time'] += diff
                offset += diff
            else:
                # 配音小于原时长，添加静音
                merged_audio += AudioSegment.silent(duration=abs(diff))

            if i > 0:
                silence_duration = it['start_time'] - queue_tts[i - 1]['end_time']
                # 前面一个和当前之间存在静音区间
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence
            if config.settings['force_edit_srt']:
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
            else:
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time_source'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time_source'])
            queue_tts[i] = it
            merged_audio += segment

        # 移除尾部静音
        co2 = merged_audio
        if config.settings['remove_silence'] or (video_time > 0 and merged_audio and (len(merged_audio) > video_time)):
            merged_audio = tools.remove_silence_from_end(merged_audio, silence_threshold=-50.0, chunk_size=10,
                                                         is_start=False)
            if isinstance(merged_audio, str):
                merged_audio = co2

        if video_time > 0 and merged_audio and (len(merged_audio) < video_time):
            # 末尾补静音
            silence = AudioSegment.silent(duration=video_time - len(merged_audio))
            merged_audio += silence

        # 创建配音后的文件
        try:
            wavfile = self.cache_folder + "/target.wav"
            merged_audio.export(wavfile, format="wav")

            if not self.source_mp4 and self.background_music and Path(self.background_music).exists():
                cmd = ['-y', '-i', wavfile, '-i', self.background_music, '-filter_complex',
                       "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.targetdir_target_wav]
                tools.runffmpeg(cmd)
            else:
                tools.wav2m4a(wavfile, self.targetdir_target_wav)
        except Exception as e:
            raise Exception(f'[error]merged_audio:{str(e)}')

        return len(merged_audio), queue_tts

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        if isinstance(srtstr, list):
            txt = ""
            for it in srtstr:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = startraw.strip().replace('.', ',')
                endraw = endraw.strip().replace('.', ',')
                startraw = tools.format_time(startraw, ',')
                endraw = tools.format_time(endraw, ',')
                txt += f"{it['line']}\n{startraw} --> {endraw}\n{it['text']}\n\n"
            with open(file, 'w', encoding="utf-8") as f:
                f.write(txt)
            time.sleep(1)
            tools.set_process(txt, 'replace_subtitle', btnkey=self.btnkey)
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def _before_tts(self):
        # 整合一个队列到 exec_tts 执行
        if self.config_params['voice_role'] == 'No':
            return True
        queue_tts = []
        # 获取字幕
        try:
            subs = tools.get_subtitle_from_srt(self.targetdir_target_sub)
            if len(subs) < 1:
                raise Exception("字幕格式不正确，请打开查看")
        except Exception as e:
            raise Exception(f'格式化字幕失败:{str(e)}')
        rate = int(str(self.config_params['voice_rate']).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出设置的每行角色
        line_roles = self.config_params["line_roles"] if "line_roles" in self.config_params else None
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = self.config_params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            newrole = voice_role.replace('/', '-').replace('\\', '/')
            filename = f'{i}-{newrole}-{self.config_params["voice_rate"]}-{self.config_params["voice_autorate"]}-{it["text"]}'
            md5_hash = hashlib.md5()
            md5_hash.update(f"{filename}".encode('utf-8'))
            # 要保存到的文件
            # clone-voice同时也是音色复制源
            filename = self.cache_folder + "/" + md5_hash.hexdigest() + ".mp3"
            # 如果是clone-voice类型， 需要截取对应片段
            if it['end_time'] <= it['start_time']:
                continue
            if self.config_params['tts_type'] == 'clone-voice':
                if self.config_params['is_separate'] and not Path(self.targetdir_source_vocal).exists():
                    raise Exception(f'背景分离出错 {self.targetdir_source_vocal}')
                    # clone 方式文件为wav格式
                if self.app_mode != 'peiyin' and self.targetdir_source_wav and Path(self.targetdir_source_wav).exists(
                        ):
                    tools.cut_from_audio(
                        audio_file=self.targetdir_source_vocal if self.config_params[
                            'is_separate'] else self.targetdir_source_wav,
                        ss=it['startraw'],
                        to=it['endraw'],
                        out_file=filename
                    )

            queue_tts.append({
                "text": it['text'],
                "role": voice_role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "tts_type": self.config_params['tts_type'],
                "filename": filename})
        return queue_tts

    # 1. 将每个配音的实际长度加入 dubb_time
    def _add_dubb_time(self, queue_tts):
        for i, it in enumerate(queue_tts):
            it['video_add'] = 0
            # 防止开始时间比上个结束时间还小
            if i > 0 and it['start_time'] < queue_tts[i - 1]['end_time']:
                it['start_time'] = queue_tts[i - 1]['end_time']
            # 防止结束时间小于开始时间
            if it['end_time'] < it['start_time']:
                it['end_time'] = it['start_time']
            # 保存原始
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            # 记录原字母区间时长
            it['raw_duration'] = it['end_time'] - it['start_time']

            if it['end_time'] > it['start_time'] and Path(it['filename']).exists():
                it['dubb_time'] = len(AudioSegment.from_file(it['filename'], format=it['filename'].split('.')[-1]))
            else:
                # 不存在配音
                it['dubb_time'] = 0
            queue_tts[i] = it

        return queue_tts

    # 2.  移除原字幕多于配音的时长，实际是字幕结束时间向前移动，和下一条之间的空白更加多了
    def _remove_srt_silence(self, queue_tts):
        # 如果需要移除多出来的静音
        for i, it in enumerate(queue_tts):
            # 配音小于 原时长，移除默认静音
            if it['dubb_time'] > 0 and it['dubb_time'] < it['raw_duration']:
                diff = it['raw_duration'] - it['dubb_time']
                it['end_time'] -= diff
                it['raw_duration'] = it['dubb_time']
            queue_tts[i] = it
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
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                # 重新设定可用的字幕区间时长
                it['raw_duration'] = it['end_time'] - it['start_time']
                queue_tts[i] = it
                continue

            # 判断后边的开始时间比当前结束时间是否大于
            next_diff = queue_tts[i + 1]['start_time'] - it['end_time']
            if next_diff >= diff:
                # 如果大于0，有空白，添加
                it['end_time'] += diff
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                it['raw_duration'] = it['end_time'] - it['start_time']
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
            it['raw_duration'] = it['end_time'] - it['start_time']
            it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
            it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts

    #   移除2个字幕间的间隔 config.settings[remove_white_ms] ms
    def _remove_white_ms(self, queue_tts):
        offset = 0
        for i, it in enumerate(queue_tts):
            if i > 0:
                it['start_time'] -= offset
                it['end_time'] -= offset
                # 配音小于 原时长，移除默认静音
                dt = it['start_time'] - queue_tts[i - 1]['end_time']
                if dt > config.settings['remove_white_ms']:
                    diff = config.settings['remove_white_ms']
                    it['end_time'] -= diff
                    it['start_time'] -= diff
                    offset += diff
                queue_tts[i] = it
        return queue_tts

    # 2. 先对配音加速，每条字幕信息中写入加速倍数 speed和延长的时间 add_time
    def _ajust_audio(self, queue_tts):
        # 遍历所有字幕条， 计算应该的配音加速倍数和延长的时间

        # 设置加速倍数
        for i, it in enumerate(queue_tts):
            it['speed'] = 0
            # 存在配音时进行处理 没有配音
            if it['dubb_time'] <= 0:
                queue_tts[i] = it
                continue
            it['raw_duration'] = it['end_time'] - it['start_time']
            # 配音时长 不大于 原时长，不处理
            if it['raw_duration'] <= 0 or it['dubb_time'] <= it['raw_duration']:
                queue_tts[i] = it
                continue
            it['speed'] = 1
            queue_tts[i] = it

        # 再次遍历，调整字幕开始结束时间对齐实际音频时长
        # 每次 start_time 和 end_time 需要添加的长度 offset 为当前所有 add_time 之和
        offset = 0
        for i, it in enumerate(queue_tts):
            jindu = (len(queue_tts) * 10) / (i + 1)
            if self.precent + jindu < 95:
                self.precent += jindu
            # 偏移增加
            it['start_time'] += offset
            # 结束时间还需要额外添加
            it['end_time'] += offset

            if it['speed'] < 1 or config.settings['audio_rate'] <= 1:
                # 不需要加速
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                queue_tts[i] = it
                continue

            if Path(it['filename']).exists():
                # 如果同时有视频加速，则配音压缩为原时长 + 差额的一半
                if config.settings['video_rate'] > 1:
                    half = int((it['dubb_time'] - it['raw_duration']) / 2)
                else:
                    half = 0
                # 调整音频
                tools.set_process(f"{config.transobj['dubbing speed up']} {it['speed']}", btnkey=self.btnkey)
                tmp_mp3 = f'{it["filename"]}-speed.mp3'
                tools.precise_speed_up_audio(file_path=it['filename'], out=tmp_mp3,
                                             target_duration_ms=it['raw_duration'] + half,
                                             max_rate=min(config.settings['audio_rate'], 100))

                # 加速后时间
                if Path(tmp_mp3).exists():
                    mp3_len = len(AudioSegment.from_file(tmp_mp3, format="mp3"))
                else:
                    mp3_len = 0
                it['raw_duration'] = it['end_time'] - it['start_time']
                it['filename'] = tmp_mp3

            # 更改时间戳
            it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
            it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts

    # 视频慢速 在配音加速调整后，根据字幕实际开始结束时间，裁剪视频，慢速播放实现对齐
    def _ajust_video(self, queue_tts):
        if not self.config_params['video_autorate'] or config.settings['video_rate'] <= 1:
            return queue_tts
        # 计算视频应该慢放的倍数，用当前实际的字幕时长/原始字幕时长得到倍数，如果当前时长小于等于原时长，不处理
        # 开始遍历每个时间段，如果需要视频加速，则截取 end_time_source start_time_source 时间段的视频，进行speed_video 处理
        concat_txt_arr = []
        if not tools.is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Exception("not novoice mp4")
        last_time = tools.get_video_duration(self.novoice_mp4)
        for i, it in enumerate(queue_tts):
            jindu = (len(queue_tts) * 10) / (i + 1)
            if self.precent + jindu < 95:
                self.precent += jindu
            # 如果i==0即第一个视频，前面若是还有片段，需要截取
            if i == 0:
                if it['start_time_source'] > 0:
                    before_dst = self.cache_folder + f'/{i}-before.mp4'
                    tools.cut_from_video(ss='00:00:00.000',
                                         to=tools.ms_to_time_string(ms=it['start_time_source']),
                                         source=self.novoice_mp4,
                                         out=before_dst)
                    concat_txt_arr.append(before_dst)
            elif it['start_time_source'] > queue_tts[i - 1]['end_time_source'] and it['start_time_source']<last_time:
                # 否则如果距离前一个字幕结束之间还有空白，则将此空白视频段截取
                before_dst = self.cache_folder + f'/{i}-before.mp4'
                tools.cut_from_video(ss=tools.ms_to_time_string(ms=queue_tts[i - 1]['end_time_source']),
                                     to=tools.ms_to_time_string(ms=it['start_time_source']),
                                     source=self.novoice_mp4,
                                     out=before_dst)
                concat_txt_arr.append(before_dst)
            # 当前可用时间段
            duration = it['end_time_source'] - it['start_time_source']
            audio_length = duration
            # 实际配音长度
            if Path(it['filename']).exists():
                audio_length = len(AudioSegment.from_file(it['filename'], format="mp3"))

            # 需要延长视频
            if duration > 0 and audio_length > duration:
                filename_video = self.cache_folder + f'/{i}.mp4'
                speed = round(audio_length / duration, 3)
                if speed <= 1:
                    speed = 1
                else:
                    speed = min(20, config.settings['video_rate'], speed)

                tools.set_process(f"{config.transobj['video speed down']}[{i}] {speed=}", btnkey=self.btnkey)
                # 截取原始视频
                if it['end_time_source'] > it['start_time_source'] and it['start_time_source']<last_time:
                    tools.cut_from_video(ss=tools.ms_to_time_string(ms=it['start_time']),
                                         to=tools.ms_to_time_string(
                                             ms=it['end_time_source'] if it['end_time_source'] < last_time else last_time),
                                         source=self.novoice_mp4,
                                         pts="" if speed <= 1 else speed,
                                         out=filename_video)
                    concat_txt_arr.append(filename_video)
            elif it['end_time_source'] > it['start_time_source'] and it['start_time_source']<last_time:
                filename_video = self.cache_folder + f'/{i}.mp4'
                concat_txt_arr.append(filename_video)
                # 直接截取原始片段，不慢放
                tools.cut_from_video(ss=tools.ms_to_time_string(ms=it['start_time_source']),
                                     to=tools.ms_to_time_string(
                                         ms=it['end_time_source'] if it['end_time_source'] < last_time else last_time),
                                     source=self.novoice_mp4,
                                     out=filename_video)
                tools.set_process(f"{config.transobj['video speed down']}[{i}] speed=1", btnkey=self.btnkey)
        if queue_tts[-1]['end_time_source'] < last_time:
            last_v = self.cache_folder + "/last_dur.mp4"
            tools.cut_from_video(ss=tools.ms_to_time_string(ms=queue_tts[-1]['end_time_source']),
                                 source=self.novoice_mp4,
                                 out=last_v)
            concat_txt_arr.append(last_v)
        # 将所有视频片段连接起来
        new_arr = []
        for it in concat_txt_arr:
            if Path(it).exists():
                new_arr.append(it)
        if len(new_arr) > 0:
            tools.concat_multi_mp4(filelist=concat_txt_arr, out=self.novoice_mp4)
        return queue_tts

    def _exec_tts(self, queue_tts):
        if not queue_tts or len(queue_tts) < 1:
            raise Exception(f'Queue tts length is 0')
        # 具体配音操作
        try:
            run_tts(queue_tts=copy.deepcopy(queue_tts), language=self.target_language_code, set_p=True, inst=self)
        except Exception as e:
            raise Exception(e)

        # 1.首先添加配音时间
        queue_tts = self._add_dubb_time(queue_tts)

        # 2.移除字幕多于配音的时间，实际上是字幕结束时间前移，和下一条字幕空白更多
        if config.settings['remove_srt_silence']:
            queue_tts = self._remove_srt_silence(queue_tts)

        # 3.是否需要 前后延展
        if "auto_ajust" in self.config_params and self.config_params['auto_ajust']:
            queue_tts = self._auto_ajust(queue_tts)

        # 5.从字幕间隔移除多余的毫秒数
        if config.settings['remove_white_ms'] > 0:
            queue_tts = self._remove_white_ms(queue_tts)

        # 4. 如果需要配音加速
        if self.config_params['voice_autorate'] and config.settings['audio_rate'] > 1:
            queue_tts = self._ajust_audio(queue_tts)

        # 如果仅需配音
        if self.app_mode == 'peiyin':
            segments = []
            start_times = []
            for i, it in enumerate(queue_tts):
                if it['dubb_time'] > 0 and Path(it['filename']).exists():
                    segments.append(AudioSegment.from_file(it['filename'], format=it['filename'].split('.')[-1]))
                    start_times.append(it['start_time'])
                else:
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
            self._merge_audio_segments(queue_tts=queue_tts)
            return True

        # 6.处理视频慢速
        if self.config_params['video_autorate'] and config.settings['video_rate'] > 1:
            queue_tts = self._ajust_video(queue_tts)

        # 获取 novoice_mp4的长度
        if not tools.is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Exception("not novoice mp4")
        video_time = tools.get_video_duration(self.novoice_mp4)
        audio_length, queue_tts = self._merge_audio_segments(
            video_time=video_time,
            queue_tts=copy.deepcopy(queue_tts))

        # 更新字幕
        srt = ""
        for (idx, it) in enumerate(queue_tts):
            srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
        # 字幕保存到目标文件夹
        with open(self.targetdir_target_sub, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(srt.strip())

        return True

    # 延长 novoice.mp4  duration_ms 毫秒
    def _novoicemp4_add_time(self, duration_ms):
        if duration_ms < 100:
            return
        tools.set_process(f'{config.transobj["shipinmoweiyanchang"]} {duration_ms}ms', btnkey=self.btnkey)
        if not tools.is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Exception("not novoice mp4")

        video_time = tools.get_video_duration(self.novoice_mp4)

        # 开始将 novoice_mp4 和 last_clip 合并
        shutil.copy2(self.novoice_mp4, f'{self.novoice_mp4}.raw.mp4')

        tools.cut_from_video(
            source=self.novoice_mp4,
            ss=tools.ms_to_time_string(ms=video_time - duration_ms).replace(',', '.'),
            out=self.cache_folder + "/last-clip-novoice.mp4",
            pts=10,
            fps=None if not self.video_info or not self.video_info['video_fps'] else self.video_info['video_fps']
        )

        clip_time = tools.get_video_duration(self.cache_folder + "/last-clip-novoice.mp4")

        nums = math.ceil(duration_ms / clip_time)
        nums += math.ceil(nums / 3)
        tools.concat_multi_mp4(
            filelist=[self.cache_folder + "/last-clip-novoice.mp4" for x in range(nums)],
            out=self.cache_folder + "/last-clip-novoice-all.mp4",
            fps=None if not self.video_info or not self.video_info['video_fps'] else self.video_info['video_fps']
        )

        tools.concat_multi_mp4(
            filelist=[f'{self.novoice_mp4}.raw.mp4', self.cache_folder + "/last-clip-novoice-all.mp4"],
            out=self.novoice_mp4,
            maxsec=math.ceil((video_time + duration_ms) / 1000),
            fps=None if not self.video_info or not self.video_info['video_fps'] else self.video_info['video_fps']
        )
        try:
            os.unlink(f'{self.novoice_mp4}.raw.mp4')
        except Exception as e:
            pass
        return True

    # 添加背景音乐
    def _back_music(self):
        if self.app_mode not in ["hebing", "tiqu", "peiyin"] and self.config_params[
            'voice_role'] != 'No' and Path(self.targetdir_target_wav).exists(
            ) and self.background_music and Path(self.background_music).exists():
            try:
                # 获取视频长度
                vtime = tools.get_video_info(self.novoice_mp4, video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.background_music)
                # 转为m4a
                if not self.background_music.lower().endswith('.m4a'):
                    tmpm4a = self.cache_folder + f"/background_music-1.m4a"
                    tools.wav2m4a(self.background_music, tmpm4a)
                    self.background_music = tmpm4a
                beishu = vtime / atime
                if config.settings['loop_backaudio'] and beishu > 1 and vtime - 1 > atime:
                    beishu = int(beishu)
                    # 获取延长片段
                    # 背景音频连接延长片段
                    tools.concat_multi_audio(filelist=[self.background_music for n in range(beishu + 1)],
                                             out=self.cache_folder + "/background_music-2.m4a")
                    self.background_music = self.cache_folder + "/background_music-2.m4a"
                # 背景音频降低音量
                tools.runffmpeg(
                    ['-y', '-i', self.background_music, "-filter:a", f"volume={config.settings['backaudio_volume']}",
                     '-c:a', 'aac',
                     self.cache_folder + f"/background_music-3.m4a"])
                # 背景音频和配音合并
                cmd = ['-y', '-i', self.targetdir_target_wav, '-i', self.cache_folder + f"/background_music-3.m4a",
                       '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.cache_folder + f"/lastend.m4a"]
                tools.runffmpeg(cmd)
                self.targetdir_target_wav = self.cache_folder + f"/lastend.m4a"
            except Exception as e:
                config.logger.error(f'添加背景音乐失败:{str(e)}')

    def _separate(self):
        if self.config_params['is_separate'] and Path(self.targetdir_target_wav).exists():
            try:
                # 原始背景音乐 wav,和配音后的文件m4a合并
                # 获取视频长度
                vtime = tools.get_video_info(self.novoice_mp4, video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.targetdir_source_instrument)
                if config.settings['loop_backaudio'] and atime + 1 < vtime:
                    # 延长背景音
                    cmd = ['-y', '-i', self.targetdir_source_instrument, '-ss', '00:00:00.000', '-t',
                           f'{vtime - atime}', self.cache_folder + "/yanchang.m4a"]
                    tools.runffmpeg(cmd)
                    # 背景音连接延长片段
                    tools.concat_multi_audio(
                        filelist=[self.targetdir_source_instrument, self.cache_folder + "/yanchang.m4a"],
                        out=self.cache_folder + f"/instrument-2.m4a")

                    self.targetdir_source_instrument = self.cache_folder + f"/instrument-2.m4a"
                # 背景音合并配音
                tools.backandvocal(self.targetdir_source_instrument, self.targetdir_target_wav)
            except Exception as e:
                config.logger.error('合并原始背景失败' + config.transobj['Error merging background and dubbing'] + str(e))

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def _compos_video(self):
        if self.app_mode in ['tiqu', 'peiyin']:
            return True
        # 判断novoice_mp4是否完成
        if not tools.is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Exception(config.transobj['fenlinoviceerror'])

        # 需要字幕
        if self.config_params['subtitle_type'] > 0 and not Path(self.targetdir_target_sub).exists():
            raise Exception(f"{config.transobj['No subtitles file']}: {self.targetdir_target_sub}")

        if self.precent < 90:
            self.precent = 90
        # 存放目标字幕
        target_sub_list = []
        # 存放原始字幕
        source_sub_list = []
        if self.config_params['subtitle_type'] > 0:
            try:
                target_sub_list = tools.get_subtitle_from_srt(self.targetdir_target_sub)
            except Exception as e:
                raise Exception(f'{config.transobj["Subtitles error"]}-1 :{str(e)}')
        if self.config_params['subtitle_type'] in [3, 4] and Path(self.targetdir_source_sub).exists(
                ):
            try:
                source_sub_list = tools.get_subtitle_from_srt(self.targetdir_source_sub)
            except Exception as e:
                raise Exception(f'{config.transobj["Subtitles error"]}-1 :{str(e)}')

        # 无声音视频 或 合并模式时原视频
        novoice_mp4_path=Path(self.novoice_mp4)
        novoice_mp4 = os.path.normpath(self.novoice_mp4)
        # 视频目录，用于硬字幕时进入工作目录
        mp4_dirpath = novoice_mp4_path.parent.resolve()

        # 软字幕 完整路径
        soft_srt = os.path.normpath(self.targetdir_target_sub)

        # 硬字幕仅名字 需要和视频在一起
        hard_srt = "tmp.srt"
        hard_srt_path = Path(mp4_dirpath/hard_srt)
        fontsize = f":force_style=Fontsize={config.settings['fontsize']}" if config.settings['fontsize'] > 0 else ""
        maxlen = config.settings['cjk_len'] if self.target_language_code[:2] in ["zh", "ja", "jp", "ko"] else \
            config.settings['other_len']
        maxlen_source = config.settings['cjk_len'] if self.source_language_code[:2] in ["zh", "ja", "jp", "ko"] else \
            config.settings['other_len']

        if self.precent < 90:
            self.precent = 90

        # 需要硬字幕
        if self.config_params['subtitle_type'] in [1, 3]:
            text = ""
            for i, it in enumerate(target_sub_list):
                it['text'] = textwrap.fill(it['text'], maxlen)
                text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
            hard_srt_path.write_text(text,encoding='utf-8',errors="ignore")
            os.chdir(mp4_dirpath)

        # 如果是合并字幕模式
        if self.app_mode == 'hebing':
            if self.config_params['subtitle_type'] in [1, 3]:
                tools.runffmpeg([
                    "-y",
                    "-i",
                    novoice_mp4,
                    "-c:v",
                    "libx264",
                    "-vf",
                    f"subtitles={hard_srt}{fontsize}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    'slow',
                    os.path.normpath(self.targetdir_mp4),
                ], de_format="nv12")
            else:
                # 软字幕
                tools.runffmpeg([
                    "-y",
                    "-i",
                    novoice_mp4,
                    "-i",
                    soft_srt,
                    "-c:v",
                    "copy" if self.h264 else "libx264",
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={self.subtitle_language}",
                    os.path.normpath(self.targetdir_mp4)
                ])
            self.precent = 100
            try:
                novoice_mp4_path.unlink(missing_ok=True)
                hard_srt_path.unlink(missing_ok=True)
            except Exception:
                pass
            return True
        # 需要配音但没有配音文件
        if self.config_params['voice_role'] != 'No' and not Path(self.targetdir_target_wav).exists():
            raise Exception(f"{config.transobj['Dubbing']}{config.transobj['anerror']}:{self.targetdir_target_wav}")

        # 需要双字幕
        if self.source_language_code != self.target_language_code and len(source_sub_list) > 0:
            # 双字幕 硬字幕
            if self.config_params['subtitle_type'] == 3:
                text = ""
                source_length = len(source_sub_list)
                for i, it in enumerate(target_sub_list):
                    it['text'] = textwrap.fill(it['text'], maxlen)
                    text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}"
                    if source_length > 0 and i < source_length:
                        text += "\n" + textwrap.fill(source_sub_list[i]['text'], maxlen_source).strip()
                    text += "\n\n"
                hard_srt_path.write_text(text.strip(),encoding="utf-8", errors="ignore")
                os.chdir(mp4_dirpath)

            # 双字幕 软字幕
            elif self.config_params['subtitle_type'] == 4:
                text = ""
                for i, it in enumerate(target_sub_list):
                    text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}"
                    if i < len(source_sub_list):
                        text += f"\n{source_sub_list[i]['text'].strip()}"
                    text += "\n\n"
                with open(soft_srt, 'w', encoding="utf-8", errors="ignore") as f:
                    f.write(text.strip())

        # 分离背景音和添加背景音乐
        self._back_music()
        self._separate()
        # 有配音 延长视频或音频对齐
        if self.config_params['voice_role'] != 'No' and config.settings['append_video']:
            video_time = tools.get_video_duration(novoice_mp4)
            audio_length = len(
                AudioSegment.from_file(self.targetdir_target_wav, format=self.targetdir_target_wav.split('.')[-1]))
            if audio_length > video_time:
                # 视频末尾延长
                try:
                    # 对视频末尾定格延长
                    self._novoicemp4_add_time(audio_length - video_time)
                except Exception as e:
                    raise Exception(f'{config.transobj["moweiyanchangshibai"]}:{str(e)}')
            elif video_time > audio_length:
                m = AudioSegment.from_file(self.targetdir_target_wav,
                                           format=self.targetdir_target_wav.split('.')[-1]) + AudioSegment.silent(
                    duration=video_time - audio_length)
                m.export(self.targetdir_target_wav, format=self.targetdir_target_wav.split('.')[-1])

        try:
            # 有配音有字幕
            if self.config_params['voice_role'] != 'No' and self.config_params['subtitle_type'] > 0:
                if self.config_params['subtitle_type'] in [1, 3]:
                    tools.set_process(config.transobj['peiyin-yingzimu'], btnkey=self.btnkey)
                    # 需要配音+硬字幕
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        novoice_mp4,
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        "-vf",
                        f"subtitles={hard_srt}{fontsize}",
                        '-crf',
                        f'{config.settings["crf"]}',
                        '-preset',
                        'slow',
                        os.path.normpath(self.targetdir_mp4),
                    ], de_format="nv12")
                else:
                    tools.set_process(config.transobj['peiyin-ruanzimu'], btnkey=self.btnkey)
                    # 配音+软字幕
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        novoice_mp4,
                        "-i",
                        os.path.normpath(self.targetdir_target_wav),
                        "-i",
                        soft_srt,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={self.subtitle_language}",
                        os.path.normpath(self.targetdir_mp4)
                    ])
            elif self.config_params['voice_role'] != 'No':
                # 有配音无字幕
                tools.set_process(config.transobj['onlypeiyin'], btnkey=self.btnkey)
                tools.runffmpeg([
                    "-y",
                    "-i",
                    novoice_mp4,
                    "-i",
                    os.path.normpath(self.targetdir_target_wav),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    os.path.normpath(self.targetdir_mp4)
                ])
            # 硬字幕无配音  原始 wav合并
            elif self.config_params['subtitle_type'] in [1, 3]:
                tools.set_process(config.transobj['onlyyingzimu'], btnkey=self.btnkey)
                cmd = [
                    "-y",
                    "-i",
                    novoice_mp4
                ]
                if Path(self.targetdir_source_wav).exists():
                    cmd.append('-i')
                    cmd.append(os.path.normpath(self.targetdir_source_wav))

                cmd.append('-c:v')
                cmd.append('libx264')
                if Path(self.targetdir_source_wav).exists():
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-vf",
                    f"subtitles={hard_srt}{fontsize}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    'slow',
                    os.path.normpath(self.targetdir_mp4),
                ]
                tools.runffmpeg(cmd, de_format="nv12")
            elif self.config_params['subtitle_type'] in [2, 4]:
                # 软字幕无配音
                tools.set_process(config.transobj['onlyruanzimu'], btnkey=self.btnkey)
                # 原视频
                cmd = [
                    "-y",
                    "-i",
                    novoice_mp4
                ]
                # 原配音流
                if Path(self.targetdir_source_wav).exists():
                    cmd.append("-i")
                    cmd.append(os.path.normpath(self.targetdir_source_wav))
                # 目标字幕流
                cmd += [
                    "-i",
                    soft_srt,
                    "-c:v",
                    "copy"
                ]
                if Path(self.targetdir_source_wav).exists():
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={self.subtitle_language}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    'slow', ]
                cmd.append(os.path.normpath(self.targetdir_mp4))
                tools.runffmpeg(cmd)
        except Exception as e:
            raise Exception(f'compose srt + video + audio:{str(e)}')
        self.precent = 99
        try:
            if Path(mp4_dirpath + "/tmp.srt").exists():
                Path(mp4_dirpath + "/tmp.srt").unlink(missing_ok=True)
            if not self.config_params['only_video']:
                with open(self.target_dir+f'/{"readme" if config.defaulelang != "zh" else "文件说明"}.txt','w', encoding="utf-8", errors="ignore") as f:
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
            novoice_mp4_path.unlink(missing_ok=True)
        except:
            pass
        self.precent = 100
        return True
