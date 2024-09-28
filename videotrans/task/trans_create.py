import copy
import math
import os
import re
import shutil
import textwrap
import threading
import time
from pathlib import Path
from typing import Dict

from pydub import AudioSegment

from videotrans import translator
from videotrans.configure import config
from videotrans.recognition import run as run_recogn
from videotrans.translator import run as run_trans, get_audio_code
from videotrans.tts import run as run_tts, CLONE_VOICE_TTS, COSYVOICE_TTS
from videotrans.util import tools
from ._base import BaseTask
from ._rate import SpeedRate


class TransCreate(BaseTask):
    """
    obj={name,dirname,basename,noextname,ext,target_dir,uuid}
    """

    def __init__(self, config_params: Dict = None, obj: Dict = None):
        super().__init__(config_params, obj)
        if "app_mode" not in self.config_params:
            self.config_params['app_mode']='biaozhun'

        # 存在添加的背景音乐
        if tools.vail_file(self.config_params['back_audio']):
            self.config_params['background_music'] = Path(self.config_params['back_audio']).as_posix()

        # 如果不是仅提取，则获取视频信息
        if self.config_params['app_mode'] not in ['tiqu']:
            # 获取视频信息
            try:
                self._signal(text="分析视频数据，用时可能较久请稍等.." if config.defaulelang == 'zh' else "Hold on a monment")
                self.config_params['video_info'] = tools.get_video_info(self.config_params['name'])
            except Exception as e:
                raise Exception(f"{config.transobj['get video_info error']}:{str(e)}")

            if not self.config_params['video_info']:
                raise Exception(config.transobj['get video_info error'])
            video_codec = 'h264' if self.video_codec == 264 else 'hevc'
            if self.config_params['video_info']['video_codec_name'] == video_codec and self.config_params[
                'ext'].lower() == 'mp4': self.config_params['h264'] = True

        # 临时文件夹
        if 'cache_folder' not in self.config_params or not self.config_params['cache_folder']:
            self.config_params['cache_folder'] = f"{config.TEMP_DIR}/{self.config_params['noextname']}"
        if 'target_dir' not in self.config_params or not self.config_params['target_dir']:
            self.config_params['target_dir'] = Path(self.config_params['target_dir']).as_posix()
        # 创建文件夹
        Path(self.config_params['target_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.config_params['cache_folder']).mkdir(parents=True, exist_ok=True)

        self.set_source_language(self.config_params['source_language'])

        # 如果配音角色不是No 并且不存在目标音频，则需要配音
        if self.config_params['voice_role'] != 'No':
            self.shoud_dubbing = True

        # 如果不是tiqu，则均需要合并
        if self.config_params['app_mode'] != 'tiqu':
            self.shoud_hebing = True

        # 最终需要输出的mp4视频
        self.config_params['targetdir_mp4'] = f"{self.config_params['target_dir']}/{self.config_params['noextname']}.mp4"
        self._unlink_size0(self.config_params['targetdir_mp4'])


        # 是否需要背景音分离：分离出的原始音频文件
        if self.config_params['is_separate']:
            # 背景音乐
            self.config_params['instrument'] = f"{self.config_params['target_dir']}/instrument.wav"
            # 转为8k采样率，降低文件
            self.config_params['vocal'] = f"{self.config_params['target_dir']}/vocal.wav"
            self.shoud_separate = True
            self._unlink_size0(self.config_params['instrument'])
            self._unlink_size0(self.config_params['vocal'])

        # 如果存在字幕，则视为原始语言字幕，不再识别
        if "subtitles" in self.config_params and self.config_params['subtitles'].strip():
            # 如果不存在目标语言，则视为原始语言字幕
            sub_file = self.config_params['source_sub']
            with open(sub_file, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.config_params['subtitles'].strip(), re.S | re.M)
                f.write(txt)
            self.shoud_recogn = False
        config.logger.info(f"{self.config_params=}")
        # 获取set.ini配置
        config.settings = config.parse_init()
        # 禁止修改字幕
        self._signal(text="forbid", type="disabled_edit")

        # 开启一个线程读秒
        def runing():
            t = 0
            while not self.hasend:
                if self._exit():
                    return
                time.sleep(2)
                t += 2
                self._signal(text=f"{self.status_text} {t}s???{self.precent}", type="set_precent", nologs=True)

        threading.Thread(target=runing).start()

    ### 同原始语言相关，当原始语言变化或检测出结果时，需要修改==========
    # 原始语言代码
    def set_source_language(self,source_language_code=None):
        self.config_params['source_language']=source_language_code
        source_code = self.config_params['source_language'] if self.config_params['source_language'] in config.langlist else config.rev_langlist.get(self.config_params['source_language'], None)
        if source_code:
            self.config_params['source_language_code'] = source_code
        # 检测字幕原始语言
        self.config_params['detect_language'] = get_audio_code(show_source=self.config_params['source_language_code'])
        # 原始语言一定存在
        self.config_params['source_sub'] = f"{self.config_params['target_dir']}/{self.config_params['source_language_code']}.srt"
        self._unlink_size0(self.config_params['source_sub'])
        # 原始语言wav
        self.config_params['source_wav'] = f"{self.config_params['target_dir']}/{self.config_params['source_language_code']}.m4a"

        self._unlink_size0(self.config_params['source_wav'])

        if self.config_params['source_language_code']!='auto' and Path(f"{self.config_params['target_dir']}/auto.m4a").exists():
            Path(f"{self.config_params['target_dir']}/auto.m4a").rename(self.config_params['source_wav'])
        # 是否需要语音识别:只要不存在原始语言字幕文件就需要识别
        if not Path(self.config_params['source_sub']).exists():
            self.shoud_recogn = True
            # 作为识别音频
            self.config_params['shibie_audio'] = f"{self.config_params['target_dir']}/shibie.wav"
            self._unlink_size0(self.config_params['shibie_audio'])


        # 目标语言代码
        target_code = self.config_params['target_language'] if self.config_params['target_language'] in config.langlist else config.rev_langlist.get(self.config_params['target_language'], None)
        if target_code:
            self.config_params['target_language_code'] = target_code
        # 存放分离后的无声音mp4
        self.config_params['novoice_mp4'] = f"{self.config_params['target_dir']}/novoice.mp4"
        # 目标语言字幕文件
        if self.config_params['target_language_code']:
            self.config_params['target_sub'] = f"{self.config_params['target_dir']}/{self.config_params['target_language_code']}.srt"
            self._unlink_size0(self.config_params['target_sub'])
            # 配音后的目标语言音频文件
            self.config_params['target_wav'] = f"{self.config_params['target_dir']}/{self.config_params['target_language_code']}.m4a"
            self._unlink_size0(self.config_params['target_wav'])


        # 是否需要翻译:存在目标语言代码并且不等于原始语言，并且不存在目标字幕文件，则需要翻译
        if self.config_params['target_language_code'] and self.config_params['target_language_code'] !=  self.config_params['source_language_code'] and not Path(self.config_params['target_sub']).exists():
            self.shoud_trans = True

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.config_params['voice_role'] != 'No' and self.config_params['source_language_code'] ==  self.config_params['target_language_code']:
            self.config_params['target_wav'] = f"{self.config_params['target_dir']}/{self.config_params['target_language_code']}-dubbing.m4a"
            self._unlink_size0(self.config_params['target_wav'])

        ### 同原始语言相关，当原始语言变化或检测出结果时，需要修改==========


    # 预处理，分离音视频、分离人声等
    # 修改不规则的名字
    def prepare(self) -> None:
        if self._exit():
            return
        # super().amend()
        # 将原始视频分离为无声视频和音频
        self._split_wav_novicemp4()

    def _recogn_succeed(self) -> None:
        # 仅提取字幕
        self.precent += 5
        if self.config_params['app_mode'] == 'tiqu':
            shutil.copy2(self.config_params['source_sub'],
                         f"{self.config_params['target_dir']}/{self.config_params['noextname']}.srt")
            if not self.shoud_trans:
                self.hasend = True
                self.precent = 100
        self.status_text = config.transobj['endtiquzimu']

    # 开始识别
    def recogn(self) -> None:
        if self._exit():
            return
        if not self.shoud_recogn:
            return
        self.status_text = config.transobj['kaishitiquzimu']
        self.precent += 3
        self._signal(text=config.transobj["kaishishibie"])
        if tools.vail_file(self.config_params['source_sub']):
            self._recogn_succeed()
            return
        # 分离未完成，需等待
        while not tools.vail_file(self.config_params['source_wav']):
            self._signal(text=config.transobj["running"])
            time.sleep(1)

        try:
            if not tools.vail_file(self.config_params['shibie_audio']):
                tools.conver_to_16k(self.config_params['source_wav'], self.config_params['shibie_audio'])
            # todo
            self.status_text = '语音识别文字处理中' if config.defaulelang == 'zh' else 'Speech Recognition to Word Processing'
            raw_subtitles = run_recogn(
                # faster-whisper openai-whisper googlespeech
                recogn_type=self.config_params['recogn_type'],
                # 整体 预先 均等
                split_type=self.config_params['split_type'],
                uuid=self.uuid,
                # 模型名
                model_name=self.config_params['model_name'],
                # 识别音频
                audio_file=self.config_params['shibie_audio'],
                detect_language=self.config_params['detect_language'],
                cache_folder=self.config_params['cache_folder'],
                is_cuda=self.config_params['cuda'],
                subtitle_type=self.config_params.get('subtitle_type',0),
                inst=self)
            if self._exit():
                return
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise Exception(self.config_params['basename'] + config.transobj['recogn result is empty'].replace('{lang}',self.config_params['source_language']))
            self._save_srt_target(raw_subtitles, self.config_params['source_sub'])
            self._recogn_succeed()
            Path(self.config_params['shibie_audio']).unlink(missing_ok=True)
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 {msg} ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
            elif re.search(r'out\s+?of.*?memory', msg, re.I):
                msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
            elif re.search(r'cudnn', msg, re.I):
                msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
            self.hasend = True
            self._signal(text=msg,type='error')
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise


    def trans(self) -> None:
        if self._exit():
            return
        if not self.shoud_trans:
            return
        self.status_text = config.transobj['starttrans']

        # 如果存在目标语言字幕，前台直接使用该字幕替换
        if self._srt_vail(self.config_params['target_sub']):
            # 判断已存在的字幕文件中是否存在有效字幕纪录
            # 通知前端替换字幕
            self._signal(
                text=Path(self.config_params['target_sub']).read_text(encoding="utf-8", errors="ignore"),
                type='replace_subtitle'
            )
            return
        try:
            # todo
            # 开始翻译,从目标文件夹读取原始字幕
            rawsrt = tools.get_subtitle_from_srt(self.config_params['source_sub'], is_file=True)
            self.status_text = config.transobj['kaishitiquhefanyi']
            target_srt = run_trans(
                translate_type=self.config_params['translate_type'],
                text_list=rawsrt,
                target_language_name=self.config_params['target_language'],
                inst=self,
                uuid=self.uuid,
                source_code=self.config_params['source_language_code'])
            self._save_srt_target(target_srt, self.config_params['target_sub'])
            # 仅提取，该名字删原
            if self.config_params['app_mode'] == 'tiqu':
                shutil.copy2(self.config_params['target_sub'],f"{self.config_params['target_dir']}/{self.config_params['noextname']}-{self.config_params['target_language_code']}.srt")
                self.hasend = True
                self.precent = 100
        except Exception as e:
            self.hasend = True
            self._signal(text=str(e),type='error')
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise
        self.status_text = config.transobj['endtrans']

    def dubbing(self) -> None:
        if self._exit():
            return
        if self.config_params['app_mode'] == 'tiqu':
            self.precent = 100
            return
        if not self.shoud_dubbing:
            return

        self.status_text = config.transobj['kaishipeiyin']
        self.precent += 3
        try:
            self._tts()
        except Exception as e:
            self.hasend = True
            self._signal(text=str(e),type='error')
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise
        if self.config_params['app_mode'] in ['tiqu']:
            self.precent = 100

    def align(self) -> None:
        if self._exit():
            return
        if self.config_params['app_mode'] == 'tiqu':
            self.precent = 100
            return

        if not self.shoud_dubbing:
            return

        self.status_text = config.transobj['duiqicaozuo']
        self.precent += 3
        if self.config_params['voice_autorate'] or self.config_params['video_autorate']:
            self.status_text = '声画变速对齐阶段' if config.defaulelang == 'zh' else 'Sound & video speed alignment stage'
        try:
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.config_params['voice_autorate'] and int(config.settings['audio_rate']) > 1,
                shoud_videorate=self.config_params['video_autorate'] and int(config.settings['video_rate']) > 1,
                novoice_mp4=self.config_params['novoice_mp4'],
                noextname=self.config_params['noextname'],
                target_audio=self.config_params['target_wav']
            )
            self.queue_tts = rate_inst.run()
            # 更新字幕
            srt = ""
            for (idx, it) in enumerate(self.queue_tts):
                if not config.settings['force_edit_srt']:
                    it['startraw'] = tools.ms_to_time_string(ms=it['start_time_source'])
                    it['endraw'] = tools.ms_to_time_string(ms=it['end_time_source'])
                srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
            # 字幕保存到目标文件夹
            with  Path(self.config_params['target_sub']).open('w', encoding="utf-8") as f:
                f.write(srt.strip())
        except Exception as e:
            self.hasend = True
            self._signal(text=str(e),type='error')
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise

    # 将 视频、音频、字幕合成
    def assembling(self) -> None:
        if self._exit():
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
            self._signal(text=str(e),type='error')
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise
        self.precent = 100

    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def task_done(self) -> None:
        # 正常完成仍是 ing，手动停止变为 stop
        if self._exit():
            return

        # 提取时，删除
        if self.config_params['app_mode'] == 'tiqu':
            Path(f"{self.config_params['target_dir']}/{self.config_params['source_language_code']}.srt").unlink(
                missing_ok=True)
            Path(f"{self.config_params['target_dir']}/{self.config_params['target_language_code']}.srt").unlink(
                missing_ok=True)
        # 仅保存视频
        elif self.config_params['only_video']:
            outputpath = Path(self.config_params['target_dir'])
            for it in outputpath.iterdir():
                ext = it.suffix.lower()
                if ext != '.mp4':
                    it.unlink(missing_ok=True)
        self.hasend = True
        self.precent = 100
        self._signal(text=f"{self.config_params['name']}", type='succeed')
        tools.send_notification(config.transobj['Succeed'], f"{self.config_params['basename']}")
        if 'shound_del_name' in self.config_params:
            Path(self.config_params['shound_del_name']).unlink(missing_ok=True)

    # 分离音频 和 novoice.mp4
    def _split_wav_novicemp4(self) -> None:
        # 不是 提取字幕时，需要分离出视频
        if self.config_params['app_mode'] not in ['tiqu']:
            config.queue_novice[self.config_params['noextname']] = 'ing'
            threading.Thread(
                target=tools.split_novoice_byraw,
                args=(self.config_params['name'],
                      self.config_params['novoice_mp4'],
                      self.config_params['noextname'],
                      "copy" if self.config_params['h264'] else f"libx{self.video_codec}")).start()
            if not self.config_params['h264']:
                self.status_text = '视频需要转码，耗时可能较久..' if config.defaulelang == 'zh' else 'Video needs transcoded and take a long time..'
        else:
            config.queue_novice[self.config_params['noextname']] = 'end'

        # 添加是否保留背景选项
        if self.config_params['is_separate']:
            try:
                self._signal(text=config.transobj['Separating background music'])
                self.status_text = config.transobj['Separating background music']
                tools.split_audio_byraw(
                    self.config_params['name'],
                    self.config_params['source_wav'],
                    True,
                    uuid=self.uuid)
            except Exception as e:
                pass
            finally:
                if not tools.vail_file(self.config_params['vocal']):
                    # 分离失败
                    self.config_params['instrument'] = None
                    self.config_params['vocal'] = None
                    self.config_params['is_separate'] = False
                    self.shoud_separate = False
                elif self.shoud_recogn:
                    # 需要识别时
                    # 分离成功后转为16k待识别音频
                    tools.conver_to_16k(self.config_params['vocal'], self.config_params['shibie_audio'])
        # 不分离，或分离失败
        if not self.config_params['is_separate']:
            try:
                self.status_text = config.transobj['kaishitiquyinpin']
                tools.split_audio_byraw(self.config_params['name'], self.config_params['source_wav'])
                # 需要识别
                if self.shoud_recogn:
                    tools.conver_to_16k(self.config_params['source_wav'], self.config_params['shibie_audio'])
            except Exception as e:
                self._signal(text=str(e),type='error')
                raise
        self.status_text = config.transobj['endfenliyinpin']

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        queue_tts = []
        # 获取字幕 可能之前写入尚未释放，暂停1s等待并重试一次
        retry=2
        while 1:
            retry-=1
            try:
                time.sleep(1)
                subs = tools.get_subtitle_from_srt(self.config_params['target_sub'])
                if len(subs) < 1:
                    raise Exception(f"字幕格式不正确，请打开查看:{self.config_params['target_sub']}")
            except Exception as e:
                if retry<=0:
                    raise
                time.sleep(3)
            else:
                break
        rate = int(str(self.config_params['voice_rate']).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出设置的每行角色
        line_roles = self.config_params["line_roles"] if "line_roles" in self.config_params else None
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time']:
                continue
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = self.config_params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            # 要保存到的文件
            filename = self.config_params['cache_folder'] + "/" + tools.get_md5(
                f'{i}-{voice_role}-{time.time()}') + ".mp3"
            # 如果是clone-voice类型， 需要截取对应片段
            # 是克隆
            if self.config_params['tts_type'] in [COSYVOICE_TTS, CLONE_VOICE_TTS] and voice_role == 'clone':
                if self.config_params['is_separate'] and not tools.vail_file(self.config_params['vocal']):
                    raise Exception(
                        f"背景分离出错,请使用其他角色名" if config.defaulelang == 'zh' else 'Background separation error, please use another character name.')

                if tools.vail_file(self.config_params['source_wav']):
                    tools.cut_from_audio(
                        audio_file=self.config_params['vocal'] if self.config_params[
                            'is_separate'] else self.config_params['source_wav'],
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
                "volume": self.config_params['volume'],
                "pitch": self.config_params['pitch'],
                "tts_type": self.config_params['tts_type'],
                "filename": filename})
        self.queue_tts = queue_tts
        if not self.queue_tts or len(self.queue_tts) < 1:
            raise Exception(f'Queue tts length is 0')
        # 具体配音操作
        run_tts(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.config_params['target_language_code'],
            uuid=self.uuid,
            inst=self
        )

    
    def _novoicemp4_add_time(self, duration_ms):
        if duration_ms < 1000 or self._exit():
            return
        self._signal(text=f'{config.transobj["shipinmoweiyanchang"]} {duration_ms}ms')
        if not tools.is_novoice_mp4(self.config_params['novoice_mp4'], self.config_params['noextname'], uuid=self.uuid):
            raise Exception("not novoice mp4")

        video_time = tools.get_video_duration(self.config_params['novoice_mp4'])
        shutil.copy2(self.config_params['novoice_mp4'], self.config_params['novoice_mp4'] + ".raw.mp4")

        # 计算需要定格的时长
        freeze_duration = duration_ms/1000

        if freeze_duration <= 0:
            return
        try:
            # 构建 FFmpeg 命令
            default_codec = f"libx{config.settings['video_codec']}"
            cmd = [
                '-y',
                '-i', 
                self.config_params['novoice_mp4'],
                '-vf', 
                f'tpad=stop_mode=clone:stop_duration={freeze_duration}',
                '-c:v', 
                default_codec,  # 使用 libx264 编码器，可根据需要更改
                '-crf', f'{config.settings["crf"]}',
                '-preset', config.settings['preset'],
                self.config_params['cache_folder'] + "/last-all.mp4"
            ]
            tools.runffmpeg(cmd)
            shutil.copy2(self.config_params['cache_folder'] + "/last-all.mp4", self.config_params['novoice_mp4'])
        except Exception as  e:
            # 延长失败
            config.logger.exception(e, exc_info=True)
            shutil.copy2(self.config_params['novoice_mp4'] + ".raw.mp4", self.config_params['novoice_mp4'])
        finally:
            Path(f"{self.config_params['novoice_mp4']}.raw.mp4").unlink(missing_ok=True)


    # 添加背景音乐
    def _back_music(self) -> None:
        if self._exit() or not self.shoud_dubbing:
            return

        if tools.vail_file(self.config_params['target_wav']) and tools.vail_file(
                self.config_params['background_music']):
            try:
                self.status_text = '添加背景音频' if config.defaulelang == 'zh' else 'Adding background audio'
                # 获取视频长度
                vtime = tools.get_video_info(self.config_params['novoice_mp4'], video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.config_params['background_music'])

                # 转为m4a
                bgm_file = self.config_params['cache_folder'] + f'/bgm_file.m4a'
                if not self.config_params['background_music'].lower().endswith('.m4a'):
                    tools.wav2m4a(self.config_params['background_music'], bgm_file)
                    self.config_params['background_music'] = bgm_file
                else:
                    shutil.copy2(self.config_params['background_music'], bgm_file)
                    self.config_params['background_music'] = bgm_file

                beishu = math.ceil(vtime / atime)
                if config.settings['loop_backaudio'] and beishu > 1 and vtime - 1 > atime:
                    # 获取延长片段
                    file_list = [self.config_params['background_music'] for n in range(beishu + 1)]
                    concat_txt = self.config_params['cache_folder'] + f'/{time.time()}.txt'
                    tools.create_concat_txt(file_list, concat_txt=concat_txt)
                    tools.concat_multi_audio(
                        concat_txt=concat_txt,
                        out=self.config_params['cache_folder'] + "/bgm_file_extend.m4a")
                    self.config_params['background_music'] = self.config_params['cache_folder'] + "/bgm_file_extend.m4a"
                # 背景音频降低音量
                tools.runffmpeg(
                    ['-y', '-i', self.config_params['background_music'], "-filter:a",
                     f"volume={config.settings['backaudio_volume']}",
                     '-c:a', 'aac',
                     self.config_params['cache_folder'] + f"/bgm_file_extend_volume.m4a"])
                # 背景音频和配音合并
                cmd = ['-y', '-i', self.config_params['target_wav'], '-i',
                       self.config_params['cache_folder'] + f"/bgm_file_extend_volume.m4a",
                       '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.config_params['cache_folder'] + f"/lastend.m4a"]
                tools.runffmpeg(cmd)
                self.config_params['target_wav'] = self.config_params['cache_folder'] + f"/lastend.m4a"
            except Exception as e:
                config.logger.exception(f'添加背景音乐失败:{str(e)}', exc_info=True)

    def _separate(self) -> None:
        if self._exit() or not self.shoud_separate:
            return

        if tools.vail_file(self.config_params['target_wav']):
            try:
                self.status_text = '重新嵌入背景音' if config.defaulelang == 'zh' else 'Re-embedded background sounds'
                # 原始背景音乐 wav,和配音后的文件m4a合并
                # 获取视频长度
                vtime = tools.get_video_info(self.config_params['novoice_mp4'], video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.config_params['instrument'])
                beishu = math.ceil(vtime / atime)
                instrument_file = self.config_params['cache_folder'] + f'/instrument.wav'
                shutil.copy2(self.config_params['instrument'], instrument_file)
                self.config_params['instrument'] = instrument_file
                config.logger.info(f'合并背景音 {beishu=},{atime=},{vtime=}')
                if config.settings['loop_backaudio'] and atime + 1 < vtime:
                    # 背景音连接延长片段
                    file_list = [instrument_file for n in range(beishu + 1)]
                    concat_txt = self.config_params['cache_folder'] + f'/{time.time()}.txt'
                    tools.create_concat_txt(file_list, concat_txt=concat_txt)
                    tools.concat_multi_audio(concat_txt=concat_txt,
                                             out=self.config_params['cache_folder'] + "/instrument-concat.m4a")
                    self.config_params['instrument'] = self.config_params['cache_folder'] + f"/instrument-concat.m4a"
                # 背景音合并配音
                tools.backandvocal(self.config_params['instrument'], self.config_params['target_wav'])
            except Exception as e:
                config.logger.exception('合并原始背景失败' + config.transobj['Error merging background and dubbing'] + str(e),
                                        exc_info=True)

    # 处理所需字幕
    def _process_subtitles(self) -> tuple[str, str]:
        if not self.config_params['target_sub'] or not Path(self.config_params['target_sub']).exists():
            raise Exception(f'不存在有效的字幕文件' if config.defaulelang == 'zh' else 'No valid subtitle file exists')

        # 如果原始语言和目标语言相同，或不存原始语言字幕，则强制单字幕
        if (self.config_params['source_language_code'] == self.config_params['target_language_code']) or (
                not self.config_params['source_sub'] or not Path(self.config_params['source_sub']).exists()):
            if self.config_params['subtitle_type'] == 3:
                self.config_params['subtitle_type'] = 1
            elif self.config_params['subtitle_type'] == 4:
                self.config_params['subtitle_type'] = 2
        # 最终处理后需要嵌入视频的字幕
        process_end_subtitle = self.config_params['target_dir'] + f'/end.srt'
        # 硬字幕时单行字符数
        maxlen = int(
            config.settings['cjk_len'] if self.config_params['target_language_code'][:2] in ["zh", "ja", "jp",
                                                                                             "ko"] else
            config.settings['other_len'])
        target_sub_list = tools.get_subtitle_from_srt(self.config_params['target_sub'])

        # 双硬 双软字幕组装
        if self.config_params['subtitle_type'] in [3, 4]:
            maxlen_source = int(
                config.settings['cjk_len'] if self.config_params['source_language_code'][:2] in ["zh", "ja", "jp",
                                                                                                 "ko"] else
                config.settings['other_len'])
            source_sub_list = tools.get_subtitle_from_srt(self.config_params['source_sub'])
            source_length = len(source_sub_list)

            srt_string = ""
            for i, it in enumerate(target_sub_list):
                # 硬字幕换行，软字幕无需处理
                tmp = textwrap.fill(it['text'].strip(), maxlen, replace_whitespace=False) if self.config_params['subtitle_type'] == 3 else it['text'].strip()
                srt_string += f"{it['line']}\n{it['time']}\n{tmp}"
                if source_length > 0 and i < source_length:
                    srt_string += "\n" + (textwrap.fill(source_sub_list[i]['text'], maxlen_source, replace_whitespace=False).strip() if self.config_params['subtitle_type'] == 3 else source_sub_list[i]['text'])
                srt_string += "\n\n"
            with Path(f"{self.config_params['target_dir']}/shuang.srt").open('w', encoding='utf-8') as f:
                f.write(srt_string.strip())
            process_end_subtitle = f"{self.config_params['target_dir']}/shuang.srt"
        elif self.config_params['subtitle_type'] == 1:
            # 单硬字幕，需处理字符数换行
            srt_string = ""
            for i, it in enumerate(target_sub_list):
                tmp = textwrap.fill(it['text'].strip(), maxlen, replace_whitespace=False)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)
        else:
            # 单软字幕
            process_end_subtitle = self.config_params['target_sub']

        # 目标字幕语言
        subtitle_langcode = translator.get_subtitle_code(show_target=self.config_params['target_language'])

        # 单软 或双软
        if self.config_params['subtitle_type'] in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        # 硬字幕转为ass格式 并设置样式
        process_end_subtitle_ass = tools.set_ass_font(process_end_subtitle)
        return os.path.basename(process_end_subtitle_ass), subtitle_langcode

    # 延长视频末尾对齐声音
    def _append_video(self) -> None:
        # 有配音 延长视频或音频对齐
        if self._exit() or not self.shoud_dubbing or not self.config_params['append_video']:
            return
        video_time = tools.get_video_duration(self.config_params['novoice_mp4'])
        try:
            audio_length = int(tools.get_audio_time(self.config_params['target_wav']) * 1000)
        except Exception:
            audio_length = 0

        if audio_length <= 0 or audio_length == video_time:
            return

        if audio_length > video_time:
            try:
                # 先对音频末尾移除静音
                tools.remove_silence_from_end(self.config_params['target_wav'], is_start=False)
                audio_length = int(tools.get_audio_time(self.config_params['target_wav']) * 1000)
            except Exception:
                audio_length = 0

        if audio_length <= 0 or audio_length == video_time:
            return

        if audio_length > video_time:
            # 视频末尾延长
            try:
                # 对视频末尾定格延长
                self.status_text = '视频末尾延长中' if config.defaulelang == 'zh' else 'Extension at the end of the video'
                self._novoicemp4_add_time(audio_length - video_time)
            except Exception as e:
                config.logger.exception(f'视频末尾延长失败:{str(e)}', exc_info=True)
        else:
            ext = self.config_params['target_wav'].split('.')[-1]
            m = AudioSegment.from_file(
                self.config_params['target_wav'],
                format="mp4" if ext == 'm4a' else ext) + AudioSegment.silent(
                duration=video_time - audio_length)
            m.export(self.config_params['target_wav'], format="mp4" if ext == 'm4a' else ext)

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def _join_video_audio_srt(self) -> None:
        if self._exit():
            return
        if not self.shoud_hebing:
            return True

        # 判断novoice_mp4是否完成
        if not tools.is_novoice_mp4(self.config_params['novoice_mp4'], self.config_params['noextname']):
            raise Exception(config.transobj['fenlinoviceerror'])

        # 需要配音但没有配音文件
        if self.shoud_dubbing and not tools.vail_file(self.config_params['target_wav']):
            raise Exception(
                f"{config.transobj['Dubbing']}{config.transobj['anerror']}:{self.config_params['target_wav']}")

        subtitles_file, subtitle_langcode = None, None
        if self.config_params['subtitle_type'] > 0:
            subtitles_file, subtitle_langcode = self._process_subtitles()

        self.precent = 90 if self.precent < 90 else self.precent
        # 有配音 延长视频或音频对齐
        self._append_video()
        # 添加背景音乐
        self._back_music()
        # 重新嵌入分离出的背景音
        self._separate()

        self.precent = 95 if self.precent < 95 else self.precent

        protxt = config.TEMP_DIR + f"/compose{time.time()}.txt"
        threading.Thread(target=self._hebing_pro, args=(protxt,)).start()

        # 字幕嵌入时进入视频目录下
        os.chdir(Path(self.config_params['novoice_mp4']).parent.resolve())
        try:
            self.status_text = '视频+字幕+配音合并中' if config.defaulelang == 'zh' else 'Video + Subtitles + Dubbing in merge'
            # 有配音有字幕
            if self.config_params['voice_role'] != 'No' and self.config_params['subtitle_type'] > 0:
                if self.config_params['subtitle_type'] in [1, 3]:
                    self._signal(text=config.transobj['peiyin-yingzimu'])
                    # 需要配音+硬字幕
                    tools.runffmpeg([
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.config_params['novoice_mp4'],
                        "-i",
                        Path(self.config_params['target_wav']).as_posix(),
                        "-c:v",
                        f"libx{self.video_codec}",
                        "-c:a",
                        "aac",
                        "-vf",
                        f"subtitles={subtitles_file}",
                        '-crf',
                        f'{config.settings["crf"]}',
                        '-preset',
                        config.settings['preset'],
                        Path(self.config_params['targetdir_mp4']).as_posix()
                    ])
                else:
                    # 配音+软字幕
                    self._signal(text=config.transobj['peiyin-ruanzimu'])
                    tools.runffmpeg([
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.config_params['novoice_mp4'],
                        "-i",
                        Path(self.config_params['target_wav']).as_posix(),
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
                        Path(self.config_params['targetdir_mp4']).as_posix()
                    ])
            elif self.config_params['voice_role'] != 'No':
                # 有配音无字幕
                self._signal(text=config.transobj['onlypeiyin'])
                tools.runffmpeg([
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.config_params['novoice_mp4'],
                    "-i",
                    Path(self.config_params['target_wav']).as_posix(),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    Path(self.config_params['targetdir_mp4']).as_posix()
                ])
            # 硬字幕无配音  原始 wav 合并
            elif self.config_params['subtitle_type'] in [1, 3]:
                self._signal(text=config.transobj['onlyyingzimu'])
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.config_params['novoice_mp4']
                ]
                if tools.vail_file(self.config_params['source_wav']):
                    cmd.append('-i')
                    cmd.append(Path(self.config_params['source_wav']).as_posix())

                cmd.append('-c:v')
                cmd.append(f'libx{self.video_codec}')
                if tools.vail_file(self.config_params['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-vf",
                    f"subtitles={subtitles_file}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset'],
                    Path(self.config_params['targetdir_mp4']).as_posix(),
                ]
                tools.runffmpeg(cmd)
            elif self.config_params['subtitle_type'] in [2, 4]:
                # 无配音软字幕
                self._signal(text=config.transobj['onlyruanzimu'])
                # 原视频
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.config_params['novoice_mp4']
                ]
                # 原配音流
                if tools.vail_file(self.config_params['source_wav']):
                    cmd.append("-i")
                    cmd.append(Path(self.config_params['source_wav']).as_posix())
                # 目标字幕流
                cmd += [
                    "-i",
                    subtitles_file,
                    "-c:v",
                    "copy"
                ]
                if tools.vail_file(self.config_params['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={subtitle_langcode}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset']
                ]
                cmd.append(Path(self.config_params['targetdir_mp4']).as_posix())
                tools.runffmpeg(cmd)
        except Exception as e:
            msg = f'最后一步字幕配音嵌入时出错:{e}' if config.defaulelang == 'zh' else f'Error in embedding the final step of the subtitle dubbing:{e}'
            self._signal(text=msg, type='error')
            raise Exception(msg)
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
        video_time = tools.get_video_duration(self.config_params['novoice_mp4'])
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
                except Exception:
                    time.sleep(1)
                    continue
                else:
                    h, m, s = end_time.split(':')
                    precent = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) * basenum / video_time,
                                    2)
                    if self.precent + precent < 99.9:
                        self.precent += precent
                    time.sleep(1)

    # 创建说明txt
    def _create_txt(self) -> None:
        try:
            Path(self.config_params['novoice_mp4']).unlink(missing_ok=True)
            if not self.config_params['only_video']:
                with open(
                        self.config_params['target_dir'] + f'/{"readme" if config.defaulelang != "zh" else "文件说明"}.txt',
                        'w', encoding="utf-8", errors="ignore") as f:
                    f.write(f"""以下是可能生成的全部文件, 根据执行时配置的选项不同, 某些文件可能不会生成, 之所以生成这些文件和素材，是为了方便有需要的用户, 进一步使用其他软件进行处理, 而不必再进行语音导出、音视频分离、字幕识别等重复工作

        *.mp4 = 最终完成的目标视频文件
        {self.config_params['source_language_code']}.m4a|.wav = 原始视频中的音频文件(包含所有背景音和人声)
        {self.config_params['target_language_code']}.m4a = 配音后的音频文件(若选择了保留背景音乐则已混入)
        {self.config_params['source_language_code']}.srt = 原始视频中根据声音识别出的字幕文件
        {self.config_params['target_language_code']}.srt = 翻译为目标语言后字幕文件
        shuang.srt = 双语字幕
        vocal.wav = 原始视频中分离出的人声音频文件
        instrument.wav = 原始视频中分离出的背景音乐音频文件


        如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎各位小额赞助，有了一定资金支持，我将能够持续投入更多时间和精力
        捐助地址：https://github.com/jianchang512/pyvideotrans/issues/80

        ====

        Here are the descriptions of all possible files that might exist. Depending on the configuration options when executing, some files may not be generated.

        *.mp4 = The final completed target video file
        {self.config_params['source_language_code']}.m4a|.wav = The audio file in the original video (containing all sounds)
        {self.config_params['target_language_code']}.m4a = The dubbed audio file (if you choose to keep the background music, it is already mixed in)
        {self.config_params['source_language_code']}.srt = Subtitles recognized in the original video
        {self.config_params['target_language_code']}.srt = Subtitles translated into the target language
        shuang.srt = Source language and target language subtitles srt 
        vocal.wav = The vocal audio file separated from the original video
        instrument.wav = The background music audio file separated from the original video


        If you feel that this project is valuable to you and hope that it can be maintained consistently, we welcome small sponsorships. With some financial support, I will be able to continue to invest more time and energy
        Donation address: https://ko-fi.com/jianchang512


        ====

        Github: https://github.com/jianchang512/pyvideotrans
        Docs: https://pyvideotrans.com

                        """)
            Path(self.config_params['target_dir'] + f'/end.srt').unlink(missing_ok=True)
            Path(self.config_params['target_dir'] + f'/end.srt.ass').unlink(missing_ok=True)
            Path(self.config_params['target_dir'] + f'/shuang.srt.ass').unlink(missing_ok=True)
        except:
            pass
