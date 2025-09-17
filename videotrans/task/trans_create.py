import copy
import math
import os
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from videotrans import translator
from videotrans.configure import config
from videotrans.recognition import run as run_recogn, Faster_Whisper_XXL
from videotrans.translator import run as run_trans, get_audio_code
from videotrans.tts import run as run_tts, CLONE_VOICE_TTS, CHATTERBOX_TTS, COSYVOICE_TTS, F5_TTS, EDGE_TTS, AZURE_TTS, \
    ELEVENLABS_TTS
from videotrans.util import tools
from ._base import BaseTask
from ._rate import SpeedRate
from ._remove_noise import remove_noise


@dataclass
class TransCreate(BaseTask):
    # 存放原始语言字幕
    source_srt_list: List = field(default_factory=list)

    # 存放目标语言字幕
    target_srt_list: List = field(default_factory=list)
    # 原始视频时长  在慢速处理合并后，时长更新至此
    video_time: float = 0.0
    # 视频信息
    """
    {
        "video_fps":0,
        "video_codec_name":"h264",
        "audio_codec_name":"aac",
        "width":0,
        "height":0,
        "time":0
    }
    """
    video_info: Dict = field(default=None, repr=False)
    # 对视频是否执行 c:v copy 操作
    is_copy_video: bool = False
    # mp4编码类型 264 265
    video_codec_num: int = 264
    ignore_align: bool = False
    """
    obj={name,dirname,basename,noextname,ext,target_dir,uuid}
    """

    def __post_init__(self):
        # 首先，处理本类的默认配置
        cfg_default = {
            "cache_folder": None,# 当前文件的临时文件夹
            "target_dir": None,# 输出文件夹，目标视频输出文件夹

            "remove_noise": False,# 是否移除噪声
            "is_separate": False,# 是否进行人声、背景音分离
            'only_video': False,# 是否仅仅输出视频，如果是，则删除生成的其他文件

            "detect_language": None,# 字幕检测语言
            'subtitle_language': None,# 软字幕嵌入语言

            "source_language": None,# 原始语言名称或代码
            "target_language": None,#目标语言名称或代码
            "source_language_code": None,# 原始语言代码
            "target_language_code": None,# 目标语言代码

            "source_sub": None,#原始字幕文件
            "target_sub": None,#目标字幕文件
            "source_wav": "",#原始语言音频，存在于临时文件夹下
            "source_wav_output": "",#原始语言音频输出，存在于目标文件夹下
            "target_wav": "",#目标语言音频，存在于临时文件夹下
            "target_wav_output": "",#目标语言音频输出，存在于目标文件夹下

            "subtitles": None,# 已存在的字幕文本，例如预先导入的

            "novoice_mp4": None,# 从原始视频分离出的无声视频
            "noextname": None,# 去掉扩展名的原始视频名
            "targetdir_mp4": None,# 最终输出合成后的mp4
            "shibie_audio": None,#转为 pcm_s16le  16k 作为语音识别的音频文件

            "instrument": None,#分离出的背景音频
            "vocal": None,#分离出的人声音频
            "back_audio": None,# 手动添加的原始背景音音频
            'background_music': None,#手动添加的背景音频，整理后的完整路径

            'app_mode': "biaozhun",#工作模式 biaohzun tiqu

            "subtitle_type": 0,# 软硬字幕嵌入类型 0=不嵌入，1=硬字幕，2=软字幕，3=双硬，4=双软
            "volume": "+0%", # 音量
            "pitch": "+0Hz",# 音调
            "voice_rate": "+0%",#语速
            "voice_role": None,# 配音角色
        }

        final_cfg = cfg_default.copy()
        final_cfg.update(self.cfg)

        self.cfg = final_cfg
        self.video_codec_num = int(config.settings.get('video_codec', 264))

        # 设置 self.cfg, self.uuid 等基础属性
        super().__post_init__()

        if "app_mode" not in self.cfg:
            self.cfg['app_mode'] = 'biaozhun'

        # 如果存在手动添加的背景音频
        if tools.vail_file(self.cfg['back_audio']):
            self.cfg['background_music'] = Path(self.cfg['back_audio']).as_posix()

        # 如果不是仅提取，则获取视频信息
        if self.cfg['app_mode'] not in ['tiqu']:
            # 获取视频信息
            self._signal(text="分析视频数据，用时可能较久请稍等.." if config.defaulelang == 'zh' else "Hold on a monment")
            self.video_info = tools.get_video_info(self.cfg['name'])
            self.video_time = self.video_info['time']

            vcodec_name = 'h264' if self.video_codec_num == 264 else 'hevc'
            # 如果获得原始视频编码格式同需要输出编码格式一致，设 is_copy_video=True
            if self.video_info['video_codec_name'] == vcodec_name and self.video_info['color'] == 'yuv420p':
                self.is_copy_video = True

        # 临时文件夹
        if 'cache_folder' not in self.cfg or not self.cfg['cache_folder']:
            self.cfg['cache_folder'] = f"{config.TEMP_DIR}/{self.uuid}"

        # 创建文件夹
        self.cfg['target_dir'] = re.sub(r'/{2,}', '/', self.cfg['target_dir'])
        Path(self.cfg['target_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.cfg['cache_folder']).mkdir(parents=True, exist_ok=True)

        # 存放分离后的无声音mp4
        self.cfg['novoice_mp4'] = f"{self.cfg['cache_folder']}/novoice.mp4"

        # 根据语言代码设置各种原始和目标语言字幕文件名称、视频文件名称等
        self.set_source_language(self.cfg['source_language'], is_del=True)

        # 如果配音角色不是No 并且不存在目标音频，则需要配音
        if self.cfg['voice_role'] and self.cfg['voice_role'] not in ['No', '', ' '] and self.cfg[
            'target_language'] not in ['No', '-']:
            self.shoud_dubbing = True

        # 如果不是 tiqu，则均需要合并视频音频字幕
        if self.cfg['app_mode'] != 'tiqu' and (self.shoud_dubbing or self.cfg['subtitle_type'] > 0):
            self.shoud_hebing = True

        # 最终需要输出的mp4视频
        self.cfg['targetdir_mp4'] = f"{self.cfg['target_dir']}/{self.cfg['noextname']}.mp4"
        self._unlink_size0(self.cfg['targetdir_mp4'])

        # 是否需要背景音分离：分离出的原始音频文件
        if self.cfg['is_separate']:
            self.cfg['instrument'] = f"{self.cfg['cache_folder']}/instrument.wav"
            self.cfg['vocal'] = f"{self.cfg['cache_folder']}/vocal.wav"
            self._unlink_size0(self.cfg['instrument'])
            self._unlink_size0(self.cfg['vocal'])
            # 判断是否已存在
            raw_instrument = f"{self.cfg['target_dir']}/instrument.wav"
            raw_vocal = f"{self.cfg['target_dir']}/vocal.wav"
            if tools.vail_file(raw_instrument) and tools.vail_file(raw_vocal):
                shutil.copy2(raw_instrument, self.cfg['instrument'])
                shutil.copy2(raw_vocal, self.cfg['vocal'])
                tools.conver_to_16k(self.cfg['vocal'], self.cfg['shibie_audio'])

            self.shoud_separate = True

        # 如果存在字幕文本，则视为原始语言字幕，不再识别
        if "subtitles" in self.cfg and self.cfg['subtitles'].strip():
            # 如果不存在目标语言，则视为原始语言字幕
            sub_file = self.cfg['source_sub']
            with open(sub_file, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.cfg['subtitles'].strip(), re.S | re.M)
                f.write(txt)
            self.shoud_recogn = False
        # 获取高级设置选项
        config.settings = config.parse_init()
        # 禁止修改字幕
        self._signal(text="forbid", type="disabled_edit")
        # 记录最终使用的配置信息
        config.logger.info(f"最终配置信息：{self.cfg=}")

        # 开启一个线程显示进度
        def runing():
            t = time.time()
            while not self.hasend:
                if self._exit():
                    return
                time.sleep(2)
                self._signal(text=f"{self.status_text} {int(time.time() - t)}s???{self.precent}", type="set_precent", nologs=True)

        threading.Thread(target=runing).start()

    ### 同原始语言相关，当原始语言变化或检测出结果时，需要修改==========
    def set_source_language(self, source_language_code=None, is_del=False):
        self.cfg['source_language'] = source_language_code
        source_code = self.cfg['source_language'] if self.cfg['source_language'] in config.langlist else config.rev_langlist.get(self.cfg['source_language'], None)
        if source_code:
            self.cfg['source_language_code'] = source_code
        # 检测字幕原始语言
        self.cfg['detect_language'] = get_audio_code(show_source=self.cfg['source_language_code']) if self.cfg['source_language_code'] != 'auto' else 'auto'
        # 原始语言一定存在
        self.cfg['source_sub'] = f"{self.cfg['target_dir']}/{self.cfg['source_language_code']}.srt"
        # 原始语言wav
        self.cfg['source_wav_output'] = f"{self.cfg['target_dir']}/{self.cfg['source_language_code']}.wav"
        self.cfg['source_wav'] = f"{self.cfg['cache_folder']}/{self.cfg['source_language_code']}.wav"
        if self.cfg['source_language_code'] != 'auto' and Path(f"{self.cfg['cache_folder']}/auto.wav").exists():
            Path(f"{self.cfg['cache_folder']}/auto.wav").rename(self.cfg['source_wav'])
        # 是否需要语音识别:只要不存在原始语言字幕文件就需要识别
        self.shoud_recogn = True
        # 作为识别音频
        self.cfg['shibie_audio'] = f"{self.cfg['target_dir']}/shibie.wav"
        # 目标语言代码
        target_code = self.cfg['target_language'] if self.cfg['target_language'] in config.langlist else config.rev_langlist.get(self.cfg['target_language'], None)
        if target_code:
            self.cfg['target_language_code'] = target_code

        # 目标语言字幕文件
        if self.cfg['target_language_code']:
            self.cfg['target_sub'] = f"{self.cfg['target_dir']}/{self.cfg['target_language_code']}.srt"
            # 配音后的目标语言音频文件
            self.cfg['target_wav_output'] = f"{self.cfg['target_dir']}/{self.cfg['target_language_code']}.wav"
            self.cfg['target_wav'] = f"{self.cfg['cache_folder']}/target.wav"

        # 是否需要翻译:存在目标语言代码并且不等于原始语言，并且不存在目标字幕文件，则需要翻译
        if self.cfg['target_language_code'] and self.cfg['target_language_code'] != self.cfg[
            'source_language_code']:
            self.shoud_trans = True

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.cfg['voice_role'] != 'No' and self.cfg['source_language_code'] == self.cfg['target_language_code']:
            self.cfg['target_wav_output'] = f"{self.cfg['target_dir']}/{self.cfg['target_language_code']}-dubbing.wav"
            self.cfg['target_wav'] = f"{self.cfg['cache_folder']}/target-dubbing.wav"

        if is_del:
            self._unlink_size0(self.cfg['source_sub'])
            self._unlink_size0(self.cfg['target_sub'])
        try:
            # 删掉已存在的，可能会失败
            if self.cfg['source_wav']:
                Path(self.cfg['source_wav']).unlink(missing_ok=True)
            if self.cfg['source_wav_output']:
                Path(self.cfg['source_wav_output']).unlink(missing_ok=True)
            if self.cfg['target_wav']:
                Path(self.cfg['target_wav']).unlink(missing_ok=True)
            if self.cfg['target_wav_output']:
                Path(self.cfg['target_wav_output']).unlink(missing_ok=True)
            if self.cfg['shibie_audio']:
                Path(self.cfg['shibie_audio']).unlink(missing_ok=True)
        except Exception as e:
            config.logger.warn(f'删除已存在的文件时失败:{e}')

    # 1. 预处理，分离音视频、分离人声等
    def prepare(self) -> None:
        if self._exit():
            return
        # 将原始视频分离为无声视频和音频
        if self.cfg['app_mode'] not in ['tiqu']:
            config.queue_novice[self.cfg['noextname']] = 'ing'
            threading.Thread(target=self._split_novoice_byraw).start()
            if not self.is_copy_video:
                self.status_text = '视频需要转码，耗时可能较久..' if config.defaulelang == 'zh' else 'Video needs transcoded and take a long time..'
        else:
            config.queue_novice[self.cfg['noextname']] = 'end'

        # 添加是否保留背景选项
        if self.cfg['is_separate'] and ( not tools.vail_file(self.cfg['vocal']) or not tools.vail_file(self.cfg['instrument'])):
            try:
                self._signal(text=config.transobj['Separating background music'])
                self.status_text = config.transobj['Separating background music']
                self._split_audio_byraw(True)
            except:
                pass
            finally:
                if not tools.vail_file(self.cfg['vocal']) or not tools.vail_file(self.cfg['instrument']):
                    # 分离失败
                    self.cfg['instrument'] = None
                    self.cfg['vocal'] = None
                    self.cfg['is_separate'] = False
                    self.shoud_separate = False
                elif self.shoud_recogn:
                    # 分离成功后转为16k待识别音频
                    tools.conver_to_16k(self.cfg['vocal'], self.cfg['shibie_audio'])
        # 不分离，或分离失败
        if not self.cfg['is_separate']:
            self.status_text = config.transobj['kaishitiquyinpin']
            self._split_audio_byraw()
            # 需要识别
            if self.shoud_recogn:
                tools.conver_to_16k(self.cfg['source_wav'], self.cfg['shibie_audio'])

        if self.cfg['source_wav']:
            shutil.copy2(self.cfg['source_wav'],self.cfg['target_dir'] + f"/{os.path.basename(self.cfg['source_wav'])}")
        self.status_text = config.transobj['endfenliyinpin']

    def _recogn_succeed(self) -> None:
        self.precent += 5
        if self.cfg['app_mode'] == 'tiqu':
            dest_name = f"{self.cfg['target_dir']}/{self.cfg['noextname']}"
            if not self.shoud_trans:
                self.hasend = True
                self.precent = 100
                dest_name += '.srt'
                shutil.copy2(self.cfg['source_sub'], dest_name)
                Path(self.cfg['source_sub']).unlink(missing_ok=True)
            else:
                dest_name += f"-{self.cfg['source_language_code']}.srt"
                shutil.copy2(self.cfg['source_sub'], dest_name)
        self.status_text = config.transobj['endtiquzimu']

    # 开始识别
    def recogn(self) -> None:
        if self._exit():
            return
        if not self.shoud_recogn:
            return
        self.status_text = '开始识别创建字幕' if config.defaulelang == 'zh' else 'Start to create subtitles'
        self.precent += 3
        self._signal(text=config.transobj["kaishishibie"])
        if tools.vail_file(self.cfg['source_sub']):
            self._recogn_succeed()
            return

        if not tools.vail_file(self.cfg['source_wav']):
            error = "分离音频失败，请检查日志或重试" if config.defaulelang == 'zh' else "Failed to separate audio, please check the log or retry"
            tools.send_notification(error, f'{self.cfg["basename"]}')
            self.hasend = True
            raise RuntimeError(error)

        try:
            if not tools.vail_file(self.cfg['shibie_audio']):
                tools.conver_to_16k(self.cfg['source_wav'], self.cfg['shibie_audio'])

            if self.cfg['remove_noise']:
                self.status_text = '开始语音降噪处理，用时可能较久，请耐心等待' if config.defaulelang == 'zh' else 'Starting to process speech noise reduction, which may take a long time, please be patient'
                self.cfg['shibie_audio'] = remove_noise(self.cfg['shibie_audio'],f"{self.cfg['cache_folder']}/remove_noise.wav")
            self.status_text = '语音识别文字处理中' if config.defaulelang == 'zh' else 'Speech Recognition to Word Processing'

            if self.cfg['recogn_type'] == Faster_Whisper_XXL:
                import subprocess, shutil
                cmd = [
                    config.settings.get('Faster_Whisper_XXL', ''),
                    self.cfg['shibie_audio'],
                    "-f", "srt"
                ]
                if self.cfg['detect_language'] != 'auto':
                    cmd.extend(['-l', self.cfg['detect_language'].split('-')[0]])
                cmd.extend(['--model', self.cfg['model_name'], '--output_dir', self.cfg['target_dir']])
                txt_file = Path(config.settings.get('Faster_Whisper_XXL', '')).parent.as_posix() + '/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

                while 1:
                    if not config.copying:
                        break
                    time.sleep(1)
                cmdstr = " ".join(cmd)
                outsrt_file = self.cfg['target_dir'] + '/' + Path(self.cfg['shibie_audio']).stem + ".srt"
                config.logger.info(f'Faster_Whisper_XXL: {cmdstr=}\n{outsrt_file=}\n{self.cfg["source_sub"]=}')

                self._external_cmd_with_wrapper(cmd)

                if outsrt_file != self.cfg['source_sub']:
                    try:
                        shutil.copy2(outsrt_file, self.cfg['source_sub'])
                    except shutil.SameFileError:
                        pass
                self._signal(text=Path(self.cfg['source_sub']).read_text(encoding='utf-8'), type='replace_subtitle')
            else:
                raw_subtitles = run_recogn(
                    recogn_type=self.cfg['recogn_type'],
                    split_type=self.cfg['split_type'],
                    uuid=self.uuid,
                    model_name=self.cfg['model_name'],
                    audio_file=self.cfg['shibie_audio'],
                    detect_language=self.cfg['detect_language'],
                    cache_folder=self.cfg['cache_folder'],
                    is_cuda=self.cfg['cuda'],
                    subtitle_type=self.cfg.get('subtitle_type', 0),
                    target_code=self.cfg['target_language_code'] if self.shoud_trans else None,
                    inst=self)
                if self._exit():
                    return
                if not raw_subtitles or len(raw_subtitles) < 1:
                    raise RuntimeError(
                        self.cfg['basename'] + config.transobj['recogn result is empty'].replace('{lang}', self.cfg['source_language']))
                if isinstance(raw_subtitles, tuple):
                    self._save_srt_target(raw_subtitles[0], self.cfg['source_sub'])
                    self.source_srt_list = raw_subtitles[0]
                    if len(raw_subtitles) == 2:
                        self._save_srt_target(raw_subtitles[1], self.cfg['target_sub'])
                else:
                    self._save_srt_target(raw_subtitles, self.cfg['source_sub'])
                    self.source_srt_list = raw_subtitles
            self._recogn_succeed()
        except Exception as e:
            msg = f'{str(e)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 {msg} ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
            elif re.search(r'out\s+?of.*?memory', msg, re.I):
                msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
            elif re.search(r'cudnn', msg, re.I):
                msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
            self.hasend = True
            tools.send_notification(msg, f'{self.cfg["basename"]}')
            raise RuntimeError(msg)

    # 翻译字幕文件
    def trans(self) -> None:
        if self._exit():
            return
        if not self.shoud_trans:
            return
        self.status_text = config.transobj['starttrans']

        # 如果存在目标语言字幕，前台直接使用该字幕替换
        if self._srt_vail(self.cfg['target_sub']):
            self._signal(
                text=Path(self.cfg['target_sub']).read_text(encoding="utf-8", errors="ignore"),
                type='replace_subtitle'
            )
            return
        try:
            rawsrt = tools.get_subtitle_from_srt(self.cfg['source_sub'], is_file=True)
            self.status_text = config.transobj['kaishitiquhefanyi']
            target_srt = run_trans(
                translate_type=self.cfg['translate_type'],
                text_list=copy.deepcopy(rawsrt),
                inst=self,
                uuid=self.uuid,
                source_code=self.cfg['source_language_code'],
                target_code=self.cfg['target_language_code']
            )
            self._save_srt_target(self._check_target_sub(rawsrt, target_srt), self.cfg['target_sub'])

            # 仅提取，该名字删原
            if self.cfg['app_mode'] == 'tiqu':
                shutil.copy2(self.cfg['target_sub'],f"{self.cfg['target_dir']}/{self.cfg['noextname']}.srt")

                if self.cfg.get('copysrt_rawvideo'):
                    p = Path(self.cfg['name'])
                    shutil.copy2(self.cfg['target_sub'], f'{p.parent.as_posix()}/{p.stem}.srt')
                    shutil.rmtree(self.cfg['target_dir'], ignore_errors=True)
                self.hasend = True
                self.precent = 100
                try:
                    Path(self.cfg['source_sub']).unlink(missing_ok=True)
                    Path(self.cfg['target_sub']).unlink(missing_ok=True)
                except:
                    pass
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise
        self.status_text = config.transobj['endtrans']

    # 对字幕进行配音
    def dubbing(self) -> None:
        if self._exit():
            return
        if self.cfg['app_mode'] == 'tiqu':
            self.precent = 100
            return
        if not self.shoud_dubbing:
            return

        self.status_text = config.transobj['kaishipeiyin']
        self.precent += 3
        try:
            if self.cfg['voice_role'] == 'clone' and self.cfg['tts_type'] == ELEVENLABS_TTS:
                if (self.cfg['source_language_code'] != 'auto' and self.cfg['source_language_code'].split('-')[
                    0] not in config.ELEVENLABS_CLONE) or (
                        self.cfg['target_language_code'].split('-')[0] not in config.ELEVENLABS_CLONE):
                    self.hasend = True
                    raise RuntimeError('ElevenLabs: Cloning of the selected language is not supported')

                self.ignore_align = True
                from videotrans.tts._elevenlabs import ElevenLabsClone
                ElevenLabsClone(self.cfg['source_wav'], self.cfg['target_wav'], self.cfg['source_language_code'],
                                self.cfg['target_language_code']).run()
            else:
                self._tts()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise

    # 音画字幕对齐
    def align(self) -> None:
        if self._exit():
            return
        if self.cfg['app_mode'] == 'tiqu':
            self.precent = 100
            return

        if not self.shoud_dubbing or self.ignore_align:
            return

        self.status_text = config.transobj['duiqicaozuo']
        self.precent += 3
        if self.cfg['voice_autorate'] or self.cfg['video_autorate']:
            self.status_text = '声画变速对齐阶段' if config.defaulelang == 'zh' else 'Sound & video speed alignment stage'
        try:
            shoud_video_rate = self.cfg['video_autorate']
            tools.is_novoice_mp4(self.cfg['novoice_mp4'], self.cfg['noextname'])
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.cfg['voice_autorate'],
                # 视频是否需慢速，需要时对 novoice_mp4进行处理
                shoud_videorate=shoud_video_rate,
                novoice_mp4=self.cfg['novoice_mp4'],
                # 原始总时长
                raw_total_time=self.video_time,
                noextname=self.cfg['noextname'],
                target_audio=self.cfg['target_wav'],
                cache_folder=self.cfg['cache_folder']
            )
            self.queue_tts = rate_inst.run()
            # 慢速处理后，更新新视频总时长，用于音视频对齐
            try:
                self.video_time = tools.get_video_duration(self.cfg['novoice_mp4'])
            except:
                pass
            # 更新字幕
            srt = ""
            for (idx, it) in enumerate(self.queue_tts):
                srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
            # 字幕保存到目标文件夹
            with  Path(self.cfg['target_sub']).open('w', encoding="utf-8") as f:
                f.write(srt.strip())
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise

        # 成功后，如果存在 音量，则调节音量
        if self.cfg['tts_type'] not in [EDGE_TTS, AZURE_TTS] and self.cfg['volume'] != '+0%' and tools.vail_file(
                self.cfg['target_wav']):
            volume = self.cfg['volume'].replace('%', '').strip()
            try:
                volume = 1 + float(volume) / 100
                if volume != 1.0:
                    tmp_name = self.cfg['cache_folder'] + f'/volume-{volume}-{Path(self.cfg["target_wav"]).name}'
                    tools.runffmpeg(['-y', '-i', self.cfg['target_wav'], '-af', f"volume={volume}", tmp_name])
                    shutil.copy2(tmp_name, self.cfg['target_wav'])
            except:
                pass

    # 将 视频、音频、字幕合成
    def assembling(self) -> None:
        if self._exit():
            return
        if self.cfg['app_mode'] == 'tiqu':
            self.precent = 100
            return
        if not self.shoud_hebing:
            self.precent = 100
            return
        if self.precent < 95:
            self.precent += 3
        self.status_text = config.transobj['kaishihebing']
        try:
            self._join_video_audio_srt()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise
        self.precent = 100

    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def task_done(self) -> None:
        # 正常完成仍是 ing，手动停止变为 stop
        if self._exit():
            return

        # 提取时，删除
        if self.cfg['app_mode'] == 'tiqu':
            try:
                Path(f"{self.cfg['target_dir']}/{self.cfg['source_language_code']}.srt").unlink(
                    missing_ok=True)
                Path(f"{self.cfg['target_dir']}/{self.cfg['target_language_code']}.srt").unlink(
                    missing_ok=True)
            except:
                pass  # 忽略删除失败
        # 仅保存视频
        elif self.cfg['only_video']:
            outputpath = Path(self.cfg['target_dir'])
            for it in outputpath.iterdir():
                ext = it.suffix.lower()
                if ext != '.mp4':
                    try:
                        it.unlink(missing_ok=True)
                    except:
                        pass

        self.hasend = True
        self.precent = 100
        self._signal(text=f"{self.cfg['name']}", type='succeed')
        tools.send_notification(config.transobj['Succeed'], f"{self.cfg['basename']}")
        try:
            if self.cfg['only_video']:
                mp4_path = Path(self.cfg['targetdir_mp4'])
                mp4_path.rename(mp4_path.parent.parent / mp4_path.name)
                shutil.rmtree(self.cfg['target_dir'], ignore_errors=True)
            if 'shound_del_name' in self.cfg:
                Path(self.cfg['shound_del_name']).unlink(missing_ok=True)
            Path(self.cfg['shibie_audio']).unlink(missing_ok=True)
            shutil.rmtree(self.cfg['cache_folder'], ignore_errors=True)
        except Exception as e:
            config.logger.exception(e, exc_info=True)

    # 从原始视频分离出 无声视频
    def _split_novoice_byraw(self):
        cmd = [
            "-y",
            "-i",
            self.cfg['name'],
            "-an",
            "-c:v",
            "copy" if self.is_copy_video else f"libx{self.video_codec_num}"
        ]
        if not self.is_copy_video:
            cmd += ["-crf", f'{config.settings["crf"]}']
        cmd += [self.cfg['novoice_mp4']]
        return tools.runffmpeg(cmd, noextname=self.cfg['noextname'])

    # 从原始视频中分离出音频
    def _split_audio_byraw(self, is_separate=False):
        cmd = [
            "-y",
            "-i",
            self.cfg['name'],
            "-vn",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            self.cfg['source_wav']
        ]
        rs = tools.runffmpeg(cmd)
        if not is_separate:
            return rs

        # 继续人声分离
        tmpdir = config.TEMP_DIR + f"/{time.time()}"
        os.makedirs(tmpdir, exist_ok=True)
        tmpfile = tmpdir + "/raw.wav"
        tools.runffmpeg([
            "-y",
            "-i",
            self.cfg['name'],
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            tmpfile
        ])
        from videotrans.separate import st
        vocal_file = self.cfg['cache_folder'] + '/vocal.wav'
        if not tools.vail_file(vocal_file):
            self._signal(
                text=config.transobj['Separating vocals and background music, which may take a longer time'])
            st.start(audio=tmpfile, path=self.cfg['cache_folder'], uuid=self.uuid)

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        queue_tts = []
        subs = tools.get_subtitle_from_srt(self.cfg['target_sub'])
        source_subs = tools.get_subtitle_from_srt(self.cfg['source_sub'])
        if len(subs) < 1:
            raise RuntimeError(f"SRT file error:{self.cfg['target_sub']}")
        try:
            rate = int(str(self.cfg['voice_rate']).replace('%', ''))
        except:
            rate = 0
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出设置的每行角色
        line_roles = config.line_roles
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time']:
                continue
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = self.cfg['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            filename_md5 = tools.get_md5(
                f"{self.cfg['tts_type']}-{it['start_time']}-{it['end_time']}-{voice_role}-{rate}-{self.cfg['volume']}-{self.cfg['pitch']}-{len(it['text'])}-{i}")
            tmp_dict = {
                "text": it['text'],
                "line": it['line'],
                "ref_text": source_subs[i]['text'] if source_subs and i < len(source_subs) else '',
                "role": voice_role,
                "start_time_source": source_subs[i]['start_time'] if source_subs and i < len(source_subs) else it[
                    'start_time'],
                "end_time_source": source_subs[i]['end_time'] if source_subs and i < len(source_subs) else it[
                    'end_time'],
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "volume": self.cfg['volume'],
                "pitch": self.cfg['pitch'],
                "tts_type": self.cfg['tts_type'],
                "filename": config.TEMP_DIR + f"/dubbing_cache/{filename_md5}.wav"
            }
            # 如果是clone-voice类型， 需要截取对应片段
            # 是克隆
            if self.cfg['tts_type'] in [COSYVOICE_TTS, CLONE_VOICE_TTS, F5_TTS,
                                        CHATTERBOX_TTS] and voice_role == 'clone':
                if self.cfg['is_separate'] and not tools.vail_file(self.cfg['vocal']):
                    raise RuntimeError(
                        f"背景分离出错,请使用其他角色名" if config.defaulelang == 'zh' else 'Background separation error, please use another character name.')

                if tools.vail_file(self.cfg['source_wav']):
                    tmp_dict[
                        'ref_wav'] = config.TEMP_DIR + f"/dubbing_cache/{it['start_time']}-{it['end_time']}-{time.time()}-{i}.wav"
                    tools.cut_from_audio(
                        audio_file=self.cfg['vocal'] if self.cfg[
                            'is_separate'] else self.cfg['source_wav'],
                        ss=it['startraw'],
                        to=it['endraw'],
                        out_file=tmp_dict['ref_wav']
                    )
            queue_tts.append(tmp_dict)

        self.queue_tts = copy.deepcopy(queue_tts)
        Path(config.TEMP_DIR + "/dubbing_cache").mkdir(parents=True, exist_ok=True)
        if not self.queue_tts or len(self.queue_tts) < 1:
            raise RuntimeError(f'Queue tts length is 0')
        # 具体配音操作
        run_tts(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.cfg['target_language_code'],
            uuid=self.uuid,
            inst=self
        )
        if config.settings.get('save_segment_audio', False):
            outname = self.cfg['target_dir'] + f'/segment_audio_{self.cfg["noextname"]}'
            Path(outname).mkdir(parents=True, exist_ok=True)
            for it in self.queue_tts:
                text = re.sub(r'["\'*?\\/\|:<>\r\n\t]+', '', it['text'])
                name = f'{outname}/{it["line"]}-{text[:60]}.wav'
                if Path(it['filename']).exists():
                    shutil.copy2(it['filename'], name)

    # 添加背景音乐
    def _back_music(self) -> None:
        if self._exit() or not self.shoud_dubbing:
            return

        if tools.vail_file(self.cfg['target_wav']) and tools.vail_file(
                self.cfg['background_music']):
            try:
                self.status_text = '添加背景音频' if config.defaulelang == 'zh' else 'Adding background audio'
                # 获取视频长度
                vtime = tools.get_audio_time(self.cfg['target_wav'])
                # 获取背景音频长度
                atime = tools.get_audio_time(self.cfg['background_music'])
                bgm_file = self.cfg['cache_folder'] + f'/bgm_file.wav'
                self.convert_to_wav(self.cfg['background_music'], bgm_file)
                self.cfg['background_music'] = bgm_file
                beishu = math.ceil(vtime / atime)
                if config.settings['loop_backaudio'] and beishu > 1 and vtime - 1 > atime:
                    # 获取延长片段
                    file_list = [self.cfg['background_music'] for n in range(beishu + 1)]
                    concat_txt = self.cfg['cache_folder'] + f'/{time.time()}.txt'
                    tools.create_concat_txt(file_list, concat_txt=concat_txt)
                    tools.concat_multi_audio(
                        concat_txt=concat_txt,
                        out=self.cfg['cache_folder'] + "/bgm_file_extend.wav")
                    self.cfg['background_music'] = self.cfg['cache_folder'] + "/bgm_file_extend.wav"
                # 背景音频降低音量
                tools.runffmpeg(
                    ['-y',
                     '-i', self.cfg['background_music'],
                     "-filter:a", f"volume={config.settings['backaudio_volume']}",
                     '-c:a', 'pcm_s16le',
                     self.cfg['cache_folder'] + f"/bgm_file_extend_volume.wav"
                     ])
                # 背景音频和配音合并
                cmd = ['-y',
                       '-i', self.cfg['target_wav'],
                       '-i', self.cfg['cache_folder'] + f"/bgm_file_extend_volume.wav",
                       '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
                       '-ac', '2',
                       '-c:a', 'pcm_s16le',
                       self.cfg['cache_folder'] + f"/lastend.wav"
                       ]
                tools.runffmpeg(cmd)
                self.cfg['target_wav'] = self.cfg['cache_folder'] + f"/lastend.wav"
            except Exception as e:
                config.logger.exception(f'添加背景音乐失败:{str(e)}', exc_info=True)

    def _separate(self) -> None:
        if self._exit() or not self.shoud_separate:
            return
        if tools.vail_file(self.cfg['target_wav']):
            try:
                self.status_text = '重新嵌入背景音' if config.defaulelang == 'zh' else 'Re-embedded background sounds'
                vtime = tools.get_audio_time(self.cfg['target_wav'])
                atime = tools.get_audio_time(self.cfg['instrument'])
                beishu = math.ceil(vtime / atime)

                instrument_file = self.cfg['instrument']
                config.logger.info(f'合并背景音 {beishu=},{atime=},{vtime=}')
                if config.settings['loop_backaudio'] and atime + 1 < vtime:
                    # 背景音连接延长片段
                    file_list = [instrument_file for n in range(beishu + 1)]
                    concat_txt = self.cfg['cache_folder'] + f'/{time.time()}.txt'
                    tools.create_concat_txt(file_list, concat_txt=concat_txt)
                    tools.concat_multi_audio(concat_txt=concat_txt,
                                             out=self.cfg['cache_folder'] + "/instrument-concat.wav")
                    self.cfg['instrument'] = self.cfg['cache_folder'] + f"/instrument-concat.wav"
                # 背景音合并配音
                self._backandvocal(self.cfg['instrument'], self.cfg['target_wav'])
                shutil.copy2(self.cfg['instrument'], f"{self.cfg['target_dir']}/{Path(instrument_file).name}")
            except Exception as e:
                config.logger.exception(e, exc_info=True)

    # 合并后最后文件仍为 人声文件，时长需要等于人声
    def _backandvocal(self, backwav, peiyinm4a):
        import tempfile
        backwav = Path(backwav).as_posix()
        peiyinm4a = Path(peiyinm4a).as_posix()
        tmpdir = tempfile.gettempdir()
        tmpwav = Path(tmpdir + f'/{time.time()}-1.wav').as_posix()
        tmpm4a = Path(tmpdir + f'/{time.time()}.wav').as_posix()
        # 背景转为m4a文件,音量降低为0.8
        self.convert_to_wav(backwav, tmpm4a, ["-filter:a", f"volume={config.settings['backaudio_volume']}"])
        tools.runffmpeg(['-y', '-i', peiyinm4a, '-i', tmpm4a, '-filter_complex',
                         "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', "-b:a", "128k",
                         '-c:a', 'pcm_s16le', tmpwav])
        shutil.copy2(tmpwav, peiyinm4a)

    # 处理所需字幕
    def _process_subtitles(self) -> tuple[str, str]:
        config.logger.info(f"\n======准备要嵌入的字幕:{self.cfg['subtitle_type']=}=====")
        if not self.cfg['target_sub'] or not Path(self.cfg['target_sub']).exists():
            raise RuntimeError(f'不存在有效的字幕文件' if config.defaulelang == 'zh' else 'No valid subtitle file exists')

        # 如果原始语言和目标语言相同，或不存原始语言字幕，则强制单字幕
        if (self.cfg['source_language_code'] == self.cfg['target_language_code']) or (
                not self.cfg['source_sub'] or not Path(self.cfg['source_sub']).exists()):
            if self.cfg['subtitle_type'] == 3:
                self.cfg['subtitle_type'] = 1
            elif self.cfg['subtitle_type'] == 4:
                self.cfg['subtitle_type'] = 2
        # 最终处理后需要嵌入视频的字幕
        process_end_subtitle = self.cfg['cache_folder'] + f'/end.srt'
        # 硬字幕时单行字符数
        maxlen = int(
            config.settings['cjk_len'] if self.cfg['target_language_code'][:2] in ["zh", "ja", "jp", "ko", 'yu'] else
            config.settings['other_len'])
        target_sub_list = tools.get_subtitle_from_srt(self.cfg['target_sub'])

        if self.cfg['subtitle_type'] in [3, 4] and not Path(self.cfg['source_sub']).exists():
            config.logger.info(f'无源语言字幕，使用目标语言字幕')
            self.cfg['subtitle_type'] = 1 if self.cfg['subtitle_type'] == 3 else 2

        # 双硬 双软字幕组装
        if self.cfg['subtitle_type'] in [3, 4]:
            maxlen_source = int(
                config.settings['cjk_len'] if self.cfg['source_language_code'][:2] in ["zh", "ja", "jp", "ko",
                                                                                       'yu'] else
                config.settings['other_len'])
            source_sub_list = tools.get_subtitle_from_srt(self.cfg['source_sub'])
            source_length = len(source_sub_list)

            srt_string = ""
            for i, it in enumerate(target_sub_list):
                # 硬字幕换行，软字幕无需处理
                tmp = tools.textwrap(it['text'].strip(), maxlen) if self.cfg['subtitle_type'] == 3 else  it['text'].strip()
                srt_string += f"{it['line']}\n{it['time']}\n{tmp}"
                if source_length > 0 and i < source_length:
                    srt_string += "\n" + (
                        tools.textwrap(source_sub_list[i]['text'], maxlen_source).strip() if
                        self.cfg['subtitle_type'] == 3 else source_sub_list[i]['text'])
                srt_string += "\n\n"
            process_end_subtitle = f"{self.cfg['cache_folder']}/shuang.srt"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string.strip())
            shutil.copy2(process_end_subtitle, self.cfg['target_dir'] + "/shuang.srt")
        elif self.cfg['subtitle_type'] == 1:
            # 单硬字幕，需处理字符数换行
            srt_string = ""
            for i, it in enumerate(target_sub_list):
                tmp = tools.textwrap(it['text'].strip(), maxlen)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)
        else:
            # 单软字幕
            basename = os.path.basename(self.cfg['target_sub'])
            process_end_subtitle = self.cfg['cache_folder'] + f"/{basename}"
            shutil.copy2(self.cfg['target_sub'], process_end_subtitle)

        # 目标字幕语言
        subtitle_langcode = translator.get_subtitle_code(show_target=self.cfg['target_language'])

        config.logger.info(
            f'最终确定字幕嵌入类型:{self.cfg["subtitle_type"]} ,目标字幕语言:{subtitle_langcode}, 字幕文件:{process_end_subtitle}\n')
        # 单软 或双软
        if self.cfg['subtitle_type'] in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        # 硬字幕转为ass格式 并设置样式
        process_end_subtitle_ass = tools.set_ass_font(process_end_subtitle)
        basename = os.path.basename(process_end_subtitle_ass)
        return basename, subtitle_langcode

    # 最终合成视频
    def _join_video_audio_srt(self) -> None:
        if self._exit():
            return
        if not self.shoud_hebing:
            return True

        # 判断novoice_mp4是否完成
        tools.is_novoice_mp4(self.cfg['novoice_mp4'], self.cfg['noextname'])

        # 需要配音但没有配音文件
        if self.shoud_dubbing and not tools.vail_file(self.cfg['target_wav']):
            raise RuntimeError(f"{config.transobj['Dubbing']}{config.transobj['anerror']}:{self.cfg['target_wav']}")

        subtitles_file, subtitle_langcode = None, None
        if self.cfg['subtitle_type'] > 0:
            subtitles_file, subtitle_langcode = self._process_subtitles()

        self.precent = min(max(90, self.precent), 95)
        # 添加背景音乐
        self._back_music()
        # 重新嵌入分离出的背景音
        self._separate()

        self.precent = min(max(95, self.precent), 98)

        protxt = config.TEMP_DIR + f"/compose{time.time()}.txt"
        threading.Thread(target=self._hebing_pro, args=(protxt,)).start()

        # 字幕嵌入时进入视频目录下
        os.chdir(Path(self.cfg['novoice_mp4']).parent.resolve())
        if tools.vail_file(self.cfg['target_wav']):
            shutil.copy2(self.cfg['target_wav'], self.cfg['target_wav_output'])
        try:
            self.status_text = '视频+字幕+配音合并中' if config.defaulelang == 'zh' else 'Video + Subtitles + Dubbing in merge'
            cmd = []
            # 有配音有字幕
            if self.cfg['voice_role'] != 'No' and self.cfg['subtitle_type'] > 0:
                if self.cfg['subtitle_type'] in [1, 3]:
                    self._signal(text=config.transobj['peiyin-yingzimu'])
                    # 需要配音+硬字幕
                    cmd = [
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.cfg['novoice_mp4'],
                        "-i",
                        Path(self.cfg['target_wav']).as_posix(),
                        "-c:v",
                        f"libx{self.video_codec_num}",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "128k",
                        "-vf",
                        f"subtitles={subtitles_file}",
                        "-movflags",
                        "+faststart",
                        '-crf',
                        f'{config.settings["crf"]}',
                        '-preset',
                        config.settings['preset'],
                        "-shortest",
                        Path(self.cfg['targetdir_mp4']).as_posix()
                    ]
                else:
                    # 配音+软字幕
                    self._signal(text=config.transobj['peiyin-ruanzimu'])
                    cmd = [
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.cfg['novoice_mp4'],
                        "-i",
                        Path(self.cfg['target_wav']).as_posix(),
                        "-i",
                        subtitles_file,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={subtitle_langcode}",
                        "-b:a",
                        "128k",
                        "-movflags",
                        "+faststart",
                        "-shortest",
                        Path(self.cfg['targetdir_mp4']).as_posix()
                    ]
            elif self.cfg['voice_role'] != 'No':
                # 有配音无字幕
                self._signal(text=config.transobj['onlypeiyin'])
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg['novoice_mp4'],
                    "-i",
                    Path(self.cfg['target_wav']).as_posix(),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-movflags",
                    "+faststart",
                    "-shortest",
                    Path(self.cfg['targetdir_mp4']).as_posix()
                ]
            # 硬字幕无配音  原始 wav 合并
            elif self.cfg['subtitle_type'] in [1, 3]:
                self._signal(text=config.transobj['onlyyingzimu'])
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg['novoice_mp4']
                ]
                if tools.vail_file(self.cfg['source_wav']):
                    cmd.append('-i')
                    cmd.append(Path(self.cfg['source_wav']).as_posix())

                cmd.append('-c:v')
                cmd.append(f'libx{self.video_codec_num}')
                if tools.vail_file(self.cfg['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-b:a",
                    "128k",
                    "-vf",
                    f"subtitles={subtitles_file}",
                    "-movflags",
                    "+faststart",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset'],
                    "-shortest",
                    Path(self.cfg['targetdir_mp4']).as_posix(),
                ]

            elif self.cfg['subtitle_type'] in [2, 4]:
                # 无配音软字幕
                self._signal(text=config.transobj['onlyruanzimu'])
                # 原视频
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg['novoice_mp4']
                ]
                # 原配音流
                if tools.vail_file(self.cfg['source_wav']):
                    cmd.append("-i")
                    cmd.append(Path(self.cfg['source_wav']).as_posix())
                # 目标字幕流
                cmd += [
                    "-i",
                    subtitles_file,
                    "-c:v",
                    "copy"
                ]
                if tools.vail_file(self.cfg['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={subtitle_langcode}",
                    "-movflags",
                    "+faststart",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset'],
                    "-shortest",
                ]
                cmd.append(Path(self.cfg['targetdir_mp4']).as_posix())
            config.logger.info(f"\n最终确定的音视频字幕合并命令为:{cmd=}\n")
            if cmd:
                tools.runffmpeg(cmd)
        except Exception as e:
            msg = f'最后一步字幕配音嵌入时出错:{e}' if config.defaulelang == 'zh' else f'Error in embedding the final step of the subtitle dubbing:{e}'
            raise RuntimeError(msg)
        self.precent = 99
        os.chdir(config.ROOT_DIR)
        self._create_txt()
        self.precent = 100
        time.sleep(1)
        self.hasend = True
        return True

    # ffmpeg进度日志
    def _hebing_pro(self, protxt) -> None:
        basenum = 100 - self.precent
        video_time = self.video_time
        while 1:
            if self.precent >= 100:
                return
            if not os.path.exists(protxt):
                time.sleep(1)
                continue
            with open(protxt, 'r', encoding='utf-8') as f:
                content = f.read().strip().split("\n")
                if content[-1] == 'progress=end':
                    return
                idx = len(content) - 1
                end_time = "00:00:00"
                while idx > 0:
                    if content[idx].startswith('out_time='):
                        end_time = content[idx].split('=')[1].strip()
                        break
                    idx -= 1
                try:
                    h, m, s = end_time.split(':')
                except:
                    time.sleep(1)
                    continue
                else:
                    h, m, s = end_time.split(':')
                    precent = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) * basenum / video_time, 2)
                    if self.precent + 0.1 < 99:
                        self.precent += 0.1
                    else:
                        self._signal(text=config.transobj['kaishihebing'] + f' -> {precent * 100}%')
                    time.sleep(1)

    # 创建说明txt
    def _create_txt(self) -> None:
        try:
            if not self.cfg['only_video']:
                with open(
                        self.cfg['target_dir'] + f'/{"readme" if config.defaulelang != "zh" else "文件说明"}.txt',
                        'w', encoding="utf-8", errors="ignore") as f:
                    f.write(f"""以下是可能生成的全部文件, 根据执行时配置的选项不同, 某些文件可能不会生成, 之所以生成这些文件和素材，是为了方便有需要的用户, 进一步使用其他软件进行处理, 而不必再进行语音导出、音视频分离、字幕识别等重复工作

        *.mp4 = 最终完成的目标视频文件
        {self.cfg['source_language_code']}.wav = 原始视频中的音频文件(包含所有背景音和人声)
        {self.cfg['target_language_code']}.wav = 配音后的音频文件(若选择了保留背景音乐则已混入)
        {self.cfg['source_language_code']}.srt = 原始视频中根据声音识别出的字幕文件
        {self.cfg['target_language_code']}.srt = 翻译为目标语言后字幕文件
        shuang.srt = 双语字幕
        vocal.wav = 原始视频中分离出的人声音频文件
        instrument.wav = 原始视频中分离出的背景音乐音频文件


        如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎各位小额赞助，有了一定资金支持，我将能够持续投入更多时间和精力
        捐助地址：https://pvt9.com/about

        ====

        Here are the descriptions of all possible files that might exist. Depending on the configuration options when executing, some files may not be generated.

        *.mp4 = The final completed target video file
        {self.cfg['source_language_code']}.wav = The audio file in the original video (containing all sounds)
        {self.cfg['target_language_code']}.wav = The dubbed audio file (if you choose to keep the background music, it is already mixed in)
        {self.cfg['source_language_code']}.srt = Subtitles recognized in the original video
        {self.cfg['target_language_code']}.srt = Subtitles translated into the target language
        shuang.srt = Source language and target language subtitles srt 
        vocal.wav = The vocal audio file separated from the original video
        instrument.wav = The background music audio file separated from the original video


        If you feel that this project is valuable to you and hope that it can be maintained consistently, we welcome small sponsorships. With some financial support, I will be able to continue to invest more time and energy
        Donation address: https://ko-fi.com/jianchang512


        ====

        Github: https://github.com/jianchang512/pyvideotrans
        Docs: https://pvt9.com

                        """)
        except:
            pass
