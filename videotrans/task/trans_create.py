import copy, json, threading
import subprocess
import platform, glob, sys
import math
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Union

from videotrans import translator
from videotrans.configure.config import ROOT_DIR, tr, app_cfg, settings, logger
from videotrans.configure import config
from videotrans.recognition import run as run_recogn, is_allow_lang as recogn_allow_lang, FASTER_WHISPER
from videotrans.translator import run as run_trans, get_audio_code
from videotrans.tts import run as run_tts, EDGE_TTS, AZURE_TTS, SUPPORT_CLONE
from videotrans.task.simple_runnable_qt import run_in_threadpool
from ..configure import contants
from ._base import BaseTask
from videotrans.util.help_ffmpeg import get_video_codec, get_audio_time, runffmpeg, get_video_info, conver_to_16k, \
    get_video_duration, cut_from_audio, create_concat_txt, concat_multi_audio, change_speed_rubberband
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.configure.excepts import VideoTransError, FFmpegError, SpeechToTextError, DubbingSrtError

from videotrans.util.help_misc import vail_file, read_last_n_lines, is_novoice_mp4, get_md5
from videotrans.util.help_srt import get_subtitle_from_srt, delete_punc, ms_to_time_string, simple_wrap, set_ass_font


@dataclass
class TransCreate(BaseTask):
    cfg: TaskCfgVTT = field(default_factory=TaskCfgVTT, repr=False)
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
    video_info: Dict = field(default_factory=dict, repr=False)
    # 对视频是否执行 c:v copy 操作
    is_copy_video: bool = False
    # 需要输出的mp4编码类型 264 265
    video_codec_num: int = 264
    # 是否忽略音频和视频对齐
    ignore_align: bool = False

    # 是否是音频翻译任务，如果是，则到配音完毕即结束，无需合并
    is_audio_trans: bool = False
    queue_tts: List = field(default_factory=list, repr=False)
    clone_ref: str = ""
    cost_duration:float=0.0
    should_recogn2:bool=False

    def __post_init__(self):
        super().__post_init__()
        self.cost_duration=time.time()
        if not self.cfg.cache_folder:
            self.cfg.cache_folder = f"{config.TEMP_DIR}/{self.uuid}"
        # 清理缓存
        if self.cfg.clear_cache:
            if self.cfg.target_dir and Path(self.cfg.target_dir).is_dir():
                shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
            if self.cfg.cache_folder and Path(self.cfg.cache_folder).is_dir():
                shutil.rmtree(self.cfg.cache_folder, ignore_errors=True)

        self.signal(text=tr('kaishichuli'))
        # -1=不启用说话人，0=启用并且不限制说话人数量，>0+1 为最大说话人数量
        self.max_speakers = self.cfg.nums_diariz if self.cfg.enable_diariz else -1
        if self.max_speakers > 0:
            self.max_speakers += 1
        self.should_recogn = True
        # 输出编码，  264 或 265
        self.video_codec_num = int(settings.get('video_codec', 264))


        # 输出文件夹，去掉可能存在的双斜线
        #self.cfg.target_dir = re.sub(r'/{2,}', '/', self.cfg.target_dir, flags=re.I | re.S)
        # 检测字幕原始语言
        self.cfg.detect_language = get_audio_code(show_source=self.cfg.source_language_code)

        # 存放分离后的无声mp4到临时文件夹
        self.cfg.novoice_mp4 = f"{self.cfg.cache_folder}/novoice.mp4"

        # 原始语言字幕文件：输出文件夹
        self.cfg.source_sub = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt"
        # 原始语言音频文件：输出文件夹
        self.cfg.source_wav_output = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.m4a"
        # 原始语言音频文件：临时文件夹
        self.cfg.source_wav = f"{self.cfg.cache_folder}/{self.cfg.source_language_code}.wav"

        # 目标语言字幕：输出文件夹
        self.cfg.target_sub = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt"
        # 配音后的目标音频文件：输出文件夹
        self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.m4a"
        # 配音后的目标音频文件：临时文件夹
        self.cfg.target_wav = f"{self.cfg.cache_folder}/target.wav"

        # 最终需要输出的mp4视频
        self.cfg.targetdir_mp4 = f"{self.cfg.target_dir}/{self.cfg.noextname}.mp4"

        # 如果配音角色不是No 则需要配音
        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.target_language_code:
            self.should_dubbing = True

        # 如果不是 tiqu，则均需要合并视频音频字幕
        if self.cfg.app_mode != 'tiqu' and (self.should_dubbing or self.cfg.subtitle_type > 0):
            self.should_hebing = True

        # 是否需要翻译:存在目标语言代码并且不等于原始语言，则需要翻译
        if self.cfg.target_language_code and self.cfg.target_language_code != self.cfg.source_language_code:
            self.should_trans = True

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.source_language_code == self.cfg.target_language_code:
            self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}-dubbing.m4a"
            self.cfg.target_wav = f"{self.cfg.cache_folder}/target-dubbing.wav"
            self.should_dubbing = True

        # 判断如果是音频，则到生成音频结束，无需合并，并且无需分离视频、无需背景音处理
        if self.cfg.ext in contants.AUDIO_EXITS:
            self.is_audio_trans = True
            # self.cfg.is_separate = False
            self.should_hebing = False

        # 没有设置目标语言，不配音不翻译
        if not self.cfg.target_language_code:
            self.should_dubbing = False
            self.should_trans = False

        if self.cfg.voice_role == 'No':
            self.should_dubbing = False

        if self.cfg.app_mode == 'tiqu':
            self.cfg.enable_diariz = False
            self.should_dubbing = False
        self.should_separate = self.cfg.is_separate
        # 是否需要二次识别
        # 选中二次识别 and 有配音 and 非嵌入双字幕 and 有翻译即原始和目标语言非同一个
        self.should_recogn2 = self.cfg.recogn2pass and self.should_dubbing and self.cfg.subtitle_type<3 and (self.cfg.source_language_code != self.cfg.target_language_code)
        
        self.cfg.vocal = f"{self.cfg.cache_folder}/vocal.wav"
        self.cfg.instrument = f"{self.cfg.cache_folder}/instrument.wav"
        
        # 记录最终使用的配置信息
        logger.debug(f"[TransCreate]最终配置信息：{self=}\n{self.cfg=}")
        # 禁止修改字幕
        self.signal(text="forbid", type="disabled_edit")

        # 开启一个线程计时，避免看起来卡死
        def runing():
            t = time.time()
            while not self.hasend:
                if self._exit(): return
                time.sleep(1)
                self.signal(text=f"{int(time.time() - t)}???{self.precent}", type="set_precent")

        if app_cfg.exec_mode != 'cli':
            threading.Thread(target=runing, daemon=True).start()

    # 1. 预处理，分离音视频、分离人声等
    def prepare(self) -> None:
        _st=time.time()
        if self._exit(): return
        self.signal(text=tr("Hold on a monment..."))
        Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)

        # 删掉可能存在的无效文件
        self._unlink_size0([self.cfg.source_sub, self.cfg.target_sub, self.cfg.targetdir_mp4])
        # 获取视频信息
        self.video_info = get_video_info(self.cfg.name)
        # 视频时长，毫秒
        self.video_time = self.video_info['time']
        # 音频时长，毫秒
        audio_stream_len = self.video_info.get('streams_audio', 0)

        # 无视频流，不是音频，并且不是提取，报错
        if self.video_info.get('video_streams', 0) < 1 and not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            raise VideoTransError(
                tr('The video file {} does not contain valid video data and cannot be processed.', self.cfg.name))

        # 无音频流，不存在原语言字幕，报错。存在则是无声视频流
        if audio_stream_len < 1 and not vail_file(self.cfg.source_sub):
            raise VideoTransError(
                tr('There is no valid audio in the file {} and it cannot be processed. Please play it manually to confirm that there is sound.',
                   self.cfg.name))

        # 如果获得原始视频编码格式是 h264，并且色素 yuv420p, 则直接复制视频流 is_copy_video=True
        if self.video_info['video_codec_name'] == 'h264' and self.video_info['color'] == 'yuv420p':
            self.is_copy_video = True

        # 如果存在字幕文本，则视为原始语言字幕，不再识别
        if self.cfg.subtitles.strip():
            with open(self.cfg.source_sub, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.cfg.subtitles.strip(), flags=re.I | re.S)
                f.write(txt)
            self.should_recogn = False

        # 判断是否已存在人声文件，只要存在， 即使用此文件作为语音识别原料
        raw_vocal = f"{self.cfg.target_dir}/vocal.wav"
        if vail_file(raw_vocal):
            shutil.copy2(raw_vocal, self.cfg.vocal)

        raw_instrument = f"{self.cfg.target_dir}/instrument.wav"
        if vail_file(raw_instrument):
            shutil.copy2(raw_instrument, self.cfg.instrument)

        # 将原始视频分离为无声视频
        if not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            app_cfg.queue_novice[self.uuid] = 'ing'
            if not self.is_copy_video:
                self.signal(text=tr("Video needs transcoded and take a long time.."))
            run_in_threadpool(self._split_novoice_byraw)
        else:
            app_cfg.queue_novice[self.uuid] = 'end'

        # 需要人声背景声分离，并且不存在已分离好的文件
        if audio_stream_len > 0 and self.cfg.is_separate and (
                not vail_file(self.cfg.vocal) or not vail_file(self.cfg.instrument)):
            self.signal(text=tr('Separating background music'))
            try:
                self._split_audio_byraw(True)
            except Exception as e:
                logger.exception(f'分离人声背景声失败，跳过 {e}', exc_info=True)
            finally:
                if not vail_file(self.cfg.vocal) or not vail_file(self.cfg.instrument):
                    # 分离失败
                    self.cfg.is_separate = self.should_separate = False

        if audio_stream_len > 0 and not vail_file(self.cfg.source_wav) and vail_file(self.cfg.vocal):
            # 如果存在人声文件(可能仅仅分离成功人声，或者单独将其他工具分离出的人声放入目标文件夹)，则使用该文件作为语音识别文件
            
            cmd = [
                "-y",
                "-i",
                self.cfg.vocal,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                self.cfg.source_wav
            ]
            try:
                logger.debug(f'存在单独的人声文件 vocal.wav, 使用此作为语音识别原始音频')
                runffmpeg(cmd)
            except Exception as e:
                logger.exception(f'将 人声文件 转为 16000 source_wav 时失败 {e}', exc_info=True)

        # 如果还不存在原音频 self.cfg.source_wav,说明失败，强制从原视频中提取 
        if audio_stream_len > 0 and not vail_file(self.cfg.source_wav):
            self._split_audio_byraw()
        # 将分离后人声设为语音克隆参考音频
        if self.cfg.vocal and Path(self.cfg.vocal).exists():
            self.clone_ref = self.cfg.vocal
        self.signal(text=tr('endfenliyinpin'))
        logger.debug(f'[预处理阶段结束耗时]:{time.time()-_st}s')

    # 开始识别
    def recogn(self) -> None:
        _st=time.time()
        if self._exit(): return
        if not self.should_recogn: return
        self.precent += 3
        self.signal(text=tr("kaishishibie"))
        if vail_file(self.cfg.source_sub):
            self.source_srt_list = get_subtitle_from_srt(self.cfg.source_sub, is_file=True)
            if Path(self.cfg.target_dir + "/speaker.json").exists():
                shutil.copy2(self.cfg.target_dir + "/speaker.json", self.cfg.cache_folder + "/speaker.json")
            self._recogn_succeed()
            return

        if not vail_file(self.cfg.source_wav):
            raise SpeechToTextError(tr("Failed to separate audio, please check the log or retry"))
        from videotrans.util.help_down import down_file_from_ms
        # 进行降噪，结果为 16k采样
        if self.cfg.remove_noise:
            _remove_noise_wav = f"{self.cfg.cache_folder}/remove_noise.wav"
            if vail_file(_remove_noise_wav):
                self.cfg.source_wav = _remove_noise_wav
                self.clone_ref = _remove_noise_wav
                logger.debug(f'复用已存在的降噪缓存文件')
            else:
                title = tr("Starting to process speech noise reduction, which may take a long time, please be patient")
                down_file_from_ms(f'{ROOT_DIR}/models/onnx', urls=[
                    'https://modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/dpdfnet4.onnx'],
                                        callback=self._process_callback)
                from videotrans.process.prepare_audio import remove_noise
                kw = {
                    "input_file": self.cfg.source_wav if not self.cfg.vocal or not Path(self.cfg.vocal).exists() else self.cfg.vocal,
                    "output_file": _remove_noise_wav,
                    "is_cuda": self.cfg.is_cuda
                }
                try:
                    _rs = self._new_process(callback=remove_noise, title=title, is_cuda=self.cfg.is_cuda, kwargs=kw)
                    if _rs:
                        self.clone_ref = self.cfg.vocal if self.cfg.vocal and Path(self.cfg.vocal).exists() else _remove_noise_wav
                        self.cfg.source_wav = _remove_noise_wav
                    self.signal(text='remove noise end')
                except Exception as e:
                    logger.exception(f'降噪失败，跳过 {e}', exc_info=True)

        self.signal(text=tr("Speech Recognition to Word Processing"))
        raw_subtitles = run_recogn(
            recogn_type=self.cfg.recogn_type,
            uuid=self.uuid,
            model_name=self.cfg.model_name,
            audio_file=self.cfg.source_wav,# 必选 16000 采样
            detect_language=self.cfg.detect_language,
            cache_folder=self.cfg.cache_folder,
            is_cuda=self.cfg.is_cuda,
            subtitle_type=self.cfg.subtitle_type,
            max_speakers=self.max_speakers,
            llm_post=self.cfg.rephrase==1
        )
        if self._exit(): return
        if not raw_subtitles:
            raise SpeechToTextError(self.cfg.basename + tr('recogn result is empty'))

        # 如果是 tiqu，并且不需要翻译，并且需要移除标点
        if self.cfg.app_mode=='tiqu' and not self.should_trans and self.cfg.fix_punc==2:
            logger.debug('仅提取不翻译模式下，移除所有标点')
            for it in raw_subtitles:
                it['text'] = delete_punc(it['text'])

        self._save_srt_target(raw_subtitles, self.cfg.source_sub)
        self.source_srt_list = raw_subtitles

        # 中英恢复标点符号
        if self.cfg.fix_punc==1 and self.cfg.detect_language[:2] in ['zh', 'en']:
            down_file_from_ms(f'{ROOT_DIR}/models/puntc', [
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/model.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/config.yaml",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/tokens.json",
            ], callback=self._process_callback)
            from videotrans.process.prepare_audio import fix_punc
            # 预先删掉已有的标点
            text_dict = {f'{it["line"]}': re.sub(r'[,.?!，。？！]', ' ', it["text"]) for it in self.source_srt_list}
            # 序列化后传递文件路径
            text_dict_file=f'{self.cfg.cache_folder}/text_dict_file_{time.time()}.json'
            Path(text_dict_file).write_text(json.dumps(text_dict),encoding="utf-8")
            kw = {"text_dict_file": text_dict_file, "is_cuda": self.cfg.is_cuda}
            try:
                _rs = self._new_process(callback=fix_punc, title=tr("Restoring punct"), is_cuda=self.cfg.is_cuda,
                                        kwargs=kw)
                if _rs:
                    text_dict_obj=json.loads(Path(text_dict_file).read_text(encoding='utf-8'))
                    for it in self.source_srt_list:
                        it['text'] = text_dict_obj.get(f'{it["line"]}', it['text'])
                        if self.cfg.detect_language[:2] == 'en':
                            it['text'] = it['text'].replace('，', ',').replace('。', '. ').replace('？', '?').replace('！','!')
                    self._save_srt_target(self.source_srt_list, self.cfg.source_sub)
                else:
                    logger.error('标点恢复出错了，跳过')
            except Exception as e:
                logger.exception(f'标点恢复失败，跳过 {e}', exc_info=True)

        self.signal(text=Path(self.cfg.source_sub).read_text(encoding='utf-8'), type='replace_subtitle')
        # whisperx-api
        # openairecogn并且模型是gpt-4o-transcribe-diarize
        # funasr并且模型是paraformer-zh
        # deepgram
        # 以上这些本身已有说话人识别，如果已有说话人识别结果，就不再重新断句
        if Path(self.cfg.cache_folder + "/speaker.json").exists():
            self._recogn_succeed()
            self.signal(text=tr('endtiquzimu'))
            return

        if self.cfg.rephrase==1:
            # LLM重新断句
            try:
                from videotrans.translator._openaicompat import OpenAICampat
                ob = OpenAICampat(
                    ainame='chatgpt' if settings.get('llm_ai_type', 'chatgpt') != 'deepseek' else 'deepseek',
                    uuid=self.uuid)

                self.signal(text=tr("Re-segmenting..."))
                srt_list = ob.llm_segment(self.source_srt_list )
                if srt_list and len(srt_list) > len(self.source_srt_list) / 2:
                    self.source_srt_list = srt_list
                    # 保留原始字幕LLM重新断句之前的文件
                    #shutil.copy2(self.cfg.source_sub, f'{self.cfg.source_sub[:-4]}-origin_without_LLM.srt')
                    self._save_srt_target(self.source_srt_list, self.cfg.source_sub)
                else:
                    logger.error(f'重新断句失败，已恢复原样,原始字幕行:{len(self.source_srt_list)}, 重新断句后字幕行:{len(srt_list)}\n断句结果:\n{srt_list=}')
            except Exception as e:
                self.signal(text=tr("Re-segmenting Error"))
                logger.exception(f"重新断句失败，已恢复原样 {e}", exc_info=True)
        self._recogn_succeed()
        self.signal(text=tr('endtiquzimu'))
        logger.debug(f'[语音识别阶段结束耗时]:{time.time()-_st}s')

    def _recogn_succeed(self) -> None:
        self.precent += 5
        if self.cfg.app_mode == 'tiqu' and not self.should_trans:
            shutil.copy2(self.cfg.source_sub,  f"{self.cfg.target_dir}/{self.cfg.noextname}.srt")
        self.signal(text=tr('endtiquzimu'))

    # 配音后再次对配音文件进行识别，以便生成简短的字幕，
    def recogn2pass(self) -> None:
        _st=time.time()
        if not self.should_recogn2 or self._exit():
            return
        if not vail_file(self.cfg.target_wav):
            logger.debug(f'跳过二次识别，因无配音音频文件')
            return

        self.precent += 3
        self.signal(text=tr("Secondary speech recognition of dubbing files"))

        shibie_audio = f'{self.cfg.cache_folder}/recogn2pass-{time.time()}.wav'
        outsrt_file = f'{self.cfg.cache_folder}/recogn2pass-{time.time()}.srt'
        try:
            conver_to_16k(self.cfg.target_wav, shibie_audio)
        except Exception as e:
            logger.exception(f'二次识别配音音频生成字幕时，预处理音频失败，静默跳过 {e}', exc_info=True)
            return

        if not vail_file(shibie_audio):
            logger.error(f'二次识别配音音频生成字幕时，预处理音频失败，静默跳过')
            return

        try:
            # 判断原渠道是否支持目标语言的识别 self.cfg.target_language_code
            recogn_type = self.cfg.recogn_type
            model_name = self.cfg.model_name
            detect_language = self.cfg.target_language_code.split('-')[0]

            if recogn_allow_lang(langcode=self.cfg.target_language_code,
                                 recogn_type=recogn_type,
                                 model_name=model_name) is not True:
                recogn_type = FASTER_WHISPER
                model_name = 'large-v3-turbo'

            raw_subtitles = run_recogn(
                recogn_type=recogn_type,
                uuid=self.uuid,
                model_name=model_name,
                audio_file=shibie_audio,
                detect_language=detect_language,
                cache_folder=self.cfg.cache_folder,
                is_cuda=self.cfg.is_cuda,
                recogn2pass=True  # 二次识别
            )
            if self._exit(): return
            if not raw_subtitles:
                logger.error('二次识别出错：' + tr('recogn result is empty'))
                return
            
            
            # LLM重新断句 start 或者存在 recogn2-llm-resegment.txt 文件，则始终在二次识别后断句，适合 clone 角色时，关闭第一次识别后的重新断句，而单独启用二次识别后的断句，因第一次识别后如果重新断句会导致参考音频裁切不准确
            if self.cfg.rephrase==1 or Path(f'{ROOT_DIR}/recogn2-llm-resegment.txt').exists():
                try:
                    from videotrans.translator._openaicompat import OpenAICampat
                    ob = OpenAICampat(
                        ainame='chatgpt' if settings.get('llm_ai_type', 'chatgpt') != 'deepseek' else 'deepseek',
                        uuid=self.uuid)

                    self.signal(text=tr("Re-segmenting..."))
                    srt_list = ob.llm_segment(raw_subtitles,step="2")
                    if srt_list and len(srt_list) > len(raw_subtitles) / 2:
                        # 目标语言代码-recogn2_without_LLM.srt 配音文件二次识别后生成的字幕，未被LLM重新断句之前的文件
                        # 原始语言代码-origin_without_LLM.srt 原始音视频文件语音识别后生成的字幕，未被LLM重新断句之前的文件
                        #self._save_srt_target(raw_subtitles, f'{self.cfg.target_sub[:-4]}-recogn2_without_LLM.srt')
                        raw_subtitles = srt_list
                    else:
                        logger.error(f'二次识别后LLM重新断句失败，已恢复原样,原始字幕行:{len(raw_subtitles)}, 重新断句后字幕行:{len(srt_list)}\n断句结果:\n{srt_list=}')
                except Exception as e:
                    self.signal(text=tr("Re-segmenting Error"))
                    logger.exception(f"二次识别后重新断句失败，已恢复原样 {e}", exc_info=True)

            # LLM重新断句 end           
            
            if self.cfg.fix_punc==2:
                logger.debug('二次识别后，移除所有标点')
                for it in raw_subtitles:
                    it['text']=delete_punc(it['text'])
            self._save_srt_target(raw_subtitles, outsrt_file)

            if not vail_file(outsrt_file):
                logger.error(f'二次识别配音文件失败，原因未知')
                return
            # 覆盖
            shutil.copy2(outsrt_file, self.cfg.target_sub)
            self.signal(text='STT 2 pass end')
            logger.debug('二次识别成功完成')
        except Exception as e:
            logger.exception(f'二次识别配音音频生成字幕时失败，静默跳过 {e}', exc_info=True)
            return
        logger.debug(f'[二次识别阶段结束耗时]:{time.time()-_st}s')

    def diariz(self):
        _st=time.time()
        # 说话人设为1，不进行分离
        if self._exit() or not self.cfg.enable_diariz or self.max_speakers == 1 or Path(
                self.cfg.cache_folder + "/speaker.json").exists():
            return
        # built pyannote reverb ali_CAM
        speaker_type = settings.get('speaker_type', 'built')
        hf_token = settings.get('hf_token')
        if speaker_type == 'built' and self.cfg.detect_language[:2] not in ['zh', 'en']:
            logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote', 'reverb'] and not hf_token:
            logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        hf_endpoit = "https://huggingface.co"
        if speaker_type in ['pyannote', 'reverb']:
            # 判断是否可访问 huggingface.co
            try:
                import requests
                requests.head('https://huggingface.co', timeout=5)

            except Exception:
                logger.exception(f'当前选择 {speaker_type} 说话人分离模型，但无法连接到 https://huggingface.co,可能会失败', exc_info=True)
                hf_endpoit = "https://hf-mirror.com"
        from videotrans.util.help_down import down_file_from_ms, check_and_down_ms
        try:
            self.precent += 3
            title = tr(f'Begin separating the speakers') + f':{speaker_type}'
            subtitles_file=f'{self.cfg.cache_folder}/diariz-{time.time()}.json'
            Path(subtitles_file).write_text(json.dumps([[it['start_time'], it['end_time']] for it in self.source_srt_list]),encoding='utf-8')
            kw = {
                "input_file": self.cfg.source_wav,
                "subtitles_file": subtitles_file,
                "speak_file":self.cfg.cache_folder + "/speaker.json",
                "num_speakers": self.max_speakers,
                "is_cuda": self.cfg.is_cuda
            }
            if speaker_type == 'built':
                down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/seg_model.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/nemo_en_titanet_small.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx"
                ], callback=self._process_callback)
                from videotrans.process.prepare_audio import built_speakers as _run_speakers
                del kw['is_cuda']
                kw['num_speakers'] = -1 if self.max_speakers < 1 else self.max_speakers
                kw['language'] = self.cfg.detect_language
            elif speaker_type == 'ali_CAM':
                check_and_down_ms(model_id='iic/speech_campplus_speaker-diarization_common',
                                        callback=self._process_callback)
                from videotrans.process.prepare_audio import cam_speakers as _run_speakers
            elif speaker_type == 'pyannote':
                from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
            elif speaker_type == 'reverb':
                from videotrans.process.prepare_audio import reverb_speakers as _run_speakers
            else:
                logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
                return
            if speaker_type in ['pyannote', 'reverb']:
                self.signal(text='Downloading speakers models')
                from huggingface_hub import snapshot_download
                snapshot_download(
                    repo_id="pyannote/speaker-diarization-3.1" if speaker_type == 'pyannote' else "Revai/reverb-diarization-v1",
                    token=hf_token,
                    endpoint=hf_endpoit
                )

            _rs = self._new_process(callback=_run_speakers, title=title,
                                         is_cuda=self.cfg.is_cuda and speaker_type != 'built', kwargs=kw)

            if _rs:
                logger.debug('分离说话人成功完成')
                shutil.copy2(self.cfg.cache_folder + "/speaker.json", self.cfg.target_dir + "/speaker.json")
            else:
                logger.error('分离失败说话人失败')
            self.signal(text=tr('separating speakers end'))
        except Exception as e:
            logger.exception(f'说话人分离失败，跳过 {e}', exc_info=True)

        logger.debug(f'[说话人分离阶段结束耗时]:{time.time()-_st}s')

    # 翻译字幕文件
    def trans(self) -> None:
        _st=time.time()
        if self._exit() or not self.should_trans: return

        self.precent += 3
        self.signal(text=tr('starttrans'))

        # 如果存在目标语言字幕，无需继续翻译，前台直接使用该字幕替换
        if vail_file(self.cfg.target_sub):
            self.signal(
                text=Path(self.cfg.target_sub).read_text(encoding="utf-8", errors="ignore"),
                type='replace_subtitle'
            )
            return

        rawsrt = get_subtitle_from_srt(self.cfg.source_sub, is_file=True)
        self.signal(text=tr('kaishitiquhefanyi'))

        target_srt = run_trans(
            translate_type=self.cfg.translate_type,
            text_list=copy.deepcopy(rawsrt),
            uuid=self.uuid,
            source_code=self.cfg.source_language_code,
            target_code=self.cfg.target_language_code
        )
        if self._exit():  return

        # 一一核对每条字幕,翻译可能导致每条字幕开头结尾出现3个 . 符号，配音后和无需配音时，需清理
        target_srt = self.check_target_sub(rawsrt, target_srt)
        if not self.should_dubbing:
            for it in target_srt:
                it['text']=it['text'].strip('...')

        # 如果仅提取
        if self.cfg.app_mode=='tiqu':
            # 移除标点
            if self.cfg.fix_punc==2:
                logger.debug('仅提取模式下，移除所有标点')
                for it in rawsrt:
                    it['text']=delete_punc(it['text'])
                for it in target_srt:
                    it['text']=delete_punc(it['text'])
            # 保存翻译前的字幕
            self._save_srt_target(rawsrt, f"{self.cfg.target_dir}/{self.cfg.noextname}-{self.cfg.source_language_code}.srt")
            # 双语输出
            if self.cfg.output_srt > 0 and self.cfg.source_language_code != self.cfg.target_language_code:
                _source_srt_len = len(rawsrt)
                for i, it in enumerate(target_srt):
                    if i < _source_srt_len and self.cfg.output_srt == 1:
                        # 目标语言在下
                        it['text'] = ("\n".join([rawsrt[i]['text'].strip(), it['text'].strip()])).strip()
                    elif i < _source_srt_len and self.cfg.output_srt == 2:
                        it['text'] = ("\n".join([it['text'].strip(), rawsrt[i]['text'].strip()])).strip()
                
        # 翻译后的字幕
        self._save_srt_target(target_srt, self.cfg.target_sub)

        if self.cfg.app_mode == 'tiqu':
            _output_file = f"{self.cfg.target_dir}/{self.cfg.noextname}.srt"
            if self.cfg.copysrt_rawvideo:
                p = Path(self.cfg.name)
                _output_file = f'{p.parent.as_posix()}/{p.stem}.srt'
            if not Path(_output_file).exists():
                shutil.copy2(self.cfg.target_sub, _output_file)

        self.signal(text=tr('endtrans'))
        logger.debug(f'[字幕翻译阶段结束耗时]:{time.time()-_st}s')

    # 对字幕进行配音
    def dubbing(self) -> None:
        _st=time.time()
        if self._exit() or self.cfg.app_mode == 'tiqu':
            return
        if self.should_dubbing:
            self.signal(text=tr('kaishipeiyin'))
        self.precent += 3
        # 内部判断，如果不需要配音则直接跳过，然后进行后续移除标点和3个点操作，不可本方法开头跳过
        self._tts()
        # 配音完毕后，需更新 目标字幕，移除前后3个点
        if Path(self.cfg.target_sub).exists():
            subs = get_subtitle_from_srt(self.cfg.target_sub)
            if self.cfg.fix_punc==2:
                logger.debug('配音结束后，移除目标字幕中所有标点')
            for it in subs:
                it['text']=it['text'].strip('...')
                if self.cfg.fix_punc==2:
                    it['text']=delete_punc(it['text'])

        if  self.cfg.fix_punc==2 and Path(self.cfg.source_sub).exists():
            logger.debug('配音结束后，移除原始字幕中所有标点')
            subs = get_subtitle_from_srt(self.cfg.source_sub)
            for it in subs:
                it['text']=delete_punc(it['text'])
            self._save_srt_target(subs, self.cfg.source_sub)
        if self.should_dubbing:
            self.signal(text=tr('The dubbing is finished'))
            logger.debug(f'[语音合成阶段结束耗时]:{time.time()-_st}s')

    # 音画字幕对齐
    def align(self) -> None:
        _st=time.time()
        if self._exit() or self.cfg.app_mode == 'tiqu' or not self.should_dubbing or self.ignore_align:
            return

        self.signal(text=tr('duiqicaozuo'))
        self.precent += 3
        if self.cfg.voice_autorate or self.cfg.video_autorate:
            self.signal(text=tr("Sound & video speed alignment stage"))

        # 需要视频慢速，则判断无声视频是否已分离完毕
        if self.cfg.video_autorate:
            is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
        # 存在视频，则以视频长度为准
        if vail_file(self.cfg.novoice_mp4):
            self.video_time = get_video_duration(self.cfg.novoice_mp4)
        from videotrans.task._rate import SpeedRate
        rate_inst = SpeedRate(
            queue_tts=self.queue_tts,
            uuid=self.uuid,
            should_audiorate=self.cfg.voice_autorate,
            # 视频是否需慢速，需要时对 novoice_mp4进行处理
            should_videorate=self.cfg.video_autorate if not self.is_audio_trans else False,
            novoice_mp4=self.cfg.novoice_mp4 if not self.is_audio_trans else None,
            # 原始总时长
            raw_total_time=self.video_time,
            target_audio=self.cfg.target_wav,
            cache_folder=self.cfg.cache_folder,
            align_sub_audio=self.cfg.align_sub_audio,  # 均在未启用音频加速和视频慢速时才起作用
            remove_silent_mid=self.cfg.remove_silent_mid  # 均在未启用音频加速和视频慢速时才起作用
        )
        self.queue_tts = rate_inst.run()

        # 慢速处理后，更新新视频总时长，用于音视频对齐
        if vail_file(self.cfg.novoice_mp4):
            self.video_time = get_video_duration(self.cfg.novoice_mp4)

        # 对齐字幕
        if self.cfg.voice_autorate or self.cfg.video_autorate or self.cfg.align_sub_audio:
            srt = ""
            for (idx, it) in enumerate(self.queue_tts):
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
                srt += f"{idx + 1}\n{startraw} --> {endraw}\n{it['text'].strip('...')}\n\n"
            # 字幕保存到目标文件夹
            with  Path(self.cfg.target_sub).open('w', encoding="utf-8") as f:
                f.write(srt.strip())

        # 成功后，如果存在 音量，则调节音量
        if self.cfg.tts_type not in [EDGE_TTS, AZURE_TTS] and self.cfg.volume != '+0%' and vail_file(
                self.cfg.target_wav):
            volume = self.cfg.volume.replace('%', '').strip()
            try:
                volume = 1 + float(volume) / 100
                if volume != 1.0:
                    tmp_name = self.cfg.cache_folder + f'/volume-{volume}-{Path(self.cfg.target_wav).name}'
                    runffmpeg(['-y', '-i', os.path.basename(self.cfg.target_wav), '-af', f"volume={volume}",
                                     os.path.basename(tmp_name)], cmd_dir=self.cfg.cache_folder)
                    shutil.copy2(tmp_name, self.cfg.target_wav)
            except Exception as e:
                logger.exception(f'配音后调节音量失败，静默跳过 {e}', exc_info=True)

        self.signal(text=tr('Alignment phase complete, awaiting the next step'))
        logger.debug(f'[声画字幕对齐阶段结束耗时]:{time.time()-_st}s')

    # 将 视频、音频、字幕合成
    def assembling(self) -> None:
        _st=time.time()
        if self._exit() or self.is_audio_trans or self.cfg.app_mode == 'tiqu' or not self.should_hebing:
            return
        self.precent = self.precent + 3 if self.precent < 95 else self.precent
        self.signal(text=tr('kaishihebing'))
        self._join_video_audio_srt()
        logger.debug(f'[音频+字幕+画面合成阶段结束耗时]:{time.time()-_st}s')

    def task_done(self) -> None:
        if self._exit(): return
        self.precent = max(99, self.precent)

        # 提取时，删除
        if self.cfg.app_mode == 'tiqu':
            try:
                Path(f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt").unlink(
                    missing_ok=True)
                Path(f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt").unlink(
                    missing_ok=True)
            except OSError:
                logger.warning('仅提取模式时，清理中间文件失败，跳过')
            return self.set_end(True)

        if self.is_audio_trans and vail_file(self.cfg.target_wav):
            try:
                shutil.copy2(self.cfg.target_wav,
                             f"{self.cfg.target_dir}/{self.cfg.target_language_code}-{self.cfg.noextname}.wav")
            except shutil.SameFileError:
                pass

        try:
            if self.cfg.only_out_mp4:
                shutil.move(self.cfg.targetdir_mp4, Path(self.cfg.target_dir).parent / f'{self.cfg.noextname}.mp4')
                shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
        except OSError as e:
            logger.exception(f'仅输出mp4时清理临时文件移动视频位置出错，跳过 {e}', exc_info=True)

        self.set_end(True)
        logger.debug(f'[{self.cfg.name}视频翻译任务结束，总耗时]:{time.time()-self.cost_duration}s')

    # 从原始视频分离出 无声视频
    def _split_novoice_byraw(self):
        cmd = [
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            self.cfg.name,
            "-an",
            "-c:v",
            "copy" if self.is_copy_video else f"libx264"
        ]
        _name = os.path.basename(self.cfg.novoice_mp4)
        enc_qua = [] if self.is_copy_video else ['-crf', '18']
        if self.is_copy_video or settings.get('force_lib'):
            return runffmpeg(cmd + enc_qua + [_name], noextname=self.uuid, cmd_dir=self.cfg.cache_folder)

        try:
            hw_decode_args, _, vcodec, enc_args = self._get_hard_cfg(codec="264")
            cmd = [
                "-y",
                "-fflags",
                "+genpts",
            ]
            cmd += hw_decode_args

            cmd += [
                "-i",
                self.cfg.name,
                "-an",
                "-c:v",
                vcodec,
                _name
            ]
            self._subprocess(cmd)
            app_cfg.queue_novice[self.uuid] = 'end'
        except Exception as e:
            logger.exception(f'硬件分离无声视频失败,尝试软分离 {e}', exc_info=True)
            return runffmpeg([
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                self.cfg.name,
                "-an",
                "-c:v",
                "libx264",
                _name
            ], noextname=self.uuid, cmd_dir=self.cfg.cache_folder, force_cpu=True)

    # 从原始视频中分离出音频
    def _split_audio_byraw(self, is_separate=False):
        cmd = [
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            self.cfg.source_wav
        ]
        rs = runffmpeg(cmd)
        if not is_separate:
            return rs

        # 继续人声分离
        tmpfile = self.cfg.cache_folder + "/441000_ac2_raw.wav"
        runffmpeg([
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            tmpfile
        ])

        if vail_file(self.cfg.vocal) and vail_file(self.cfg.instrument):
            return
        from videotrans.util.help_down import down_file_from_ms
        title = tr('Separating vocals and background music, which may take a longer time')
        uvr_models = settings.get('uvr_models')
        if uvr_models.startswith('spleeter'):
            down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/vocals.fp16.onnx",
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/accompaniment.fp16.onnx"
            ], callback=self._process_callback)

        else:
            down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/{uvr_models}.onnx"
            ], callback=self._process_callback)
        from videotrans.process.prepare_audio import vocal_bgm
        # 返回 False None 失败
        kw = {"input_file": tmpfile, "vocal_file": self.cfg.vocal, "instr_file": self.cfg.instrument,
              "uvr_models": uvr_models}
        try:
            rs = self._new_process(callback=vocal_bgm, title=title, is_cuda=False, kwargs=kw)
            if rs and vail_file(self.cfg.vocal) and vail_file(self.cfg.instrument):
                cmd = [
                    "-y",
                    "-i",
                    self.cfg.vocal,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    '-af',
                    "volume=1.5",
                    self.cfg.source_wav
                ]
                runffmpeg(cmd)
                shutil.copy2(self.cfg.vocal, f'{self.cfg.target_dir}/vocal.wav')
                shutil.copy2(self.cfg.instrument, f'{self.cfg.target_dir}/instrument.wav')
        except Exception as e:
            logger.exception(f'人声背景声分离失败，静默跳过 {e}', exc_info=True)

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        if not self.should_dubbing:
            self.signal(text='Skip tts')
            return
        queue_tts = []
        subs = get_subtitle_from_srt(self.cfg.target_sub)
        source_subs = get_subtitle_from_srt(self.cfg.source_sub)
        if len(subs) < 1:
            raise DubbingSrtError(f"SRT file error:{self.cfg.target_sub}")
        try:
            rate = int(str(self.cfg.voice_rate).replace('%', ''))
        except (ValueError,TypeError):
            rate = 0

        rate = f"+{rate}%" if rate >= 0 else f"{rate}%"

        # 取出设置的每行角色
        line_roles = app_cfg.line_roles
        voice_role = self.cfg.voice_role
        #force_clone = str(voice_role).strip().lower() == 'clone' and self.cfg.tts_type in SUPPORT_CLONE
        logger.debug(f'{line_roles=}')
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] < it['start_time'] or not it['text'].strip():
                continue
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            #voice = 'clone' if force_clone else line_roles.get(f'{it["line"]}', voice_role)
            voice = line_roles.get(f'{it["line"]}', voice_role) if line_roles else voice_role

            _key = get_md5(f"{self.cfg.target_language_code}-{it['text']}-{voice}-{rate}-{self.cfg.volume}-{self.cfg.pitch}-{self.cfg.tts_type}")

            tmp_dict = {
                "text": it['text'],
                "line": it['line'],
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "ref_text": source_subs[i]['text'] if source_subs and i < len(source_subs) else '',
                "start_time_source": source_subs[i]['start_time'] if source_subs and i < len(source_subs) else it[
                    'start_time'],
                "end_time_source": source_subs[i]['end_time'] if source_subs and i < len(source_subs) else it[
                    'end_time'],
                "role": voice,
                "rate": rate,
                "volume": self.cfg.volume,
                "pitch": self.cfg.pitch,
                "tts_type": self.cfg.tts_type,
                "filename": f"{self.cfg.cache_folder}/dubb-{i}-{_key}.wav"
            }
            # 如果是 clone 角色， 需要截取对应片段
            if str(voice).strip().lower() == 'clone' and self.cfg.tts_type in SUPPORT_CLONE:
                tmp_dict['ref_wav'] = f"{self.cfg.cache_folder}/clone-{i}.wav"
                tmp_dict['ref_language'] = self.cfg.detect_language[:2]
            queue_tts.append(tmp_dict)

        self.queue_tts = copy.deepcopy(queue_tts)

        if not self.queue_tts or len(self.queue_tts) < 1:
            raise RuntimeError(f'字幕长度为0，无法继续配音')

        # 如果存在有 ref_wav 即需要clone，存在参考音频的
        if len([it.get("ref_wav") for it in self.queue_tts if it.get("ref_wav")]) > 0:
            self._create_ref_from_vocal()

        # 调用配音渠道
        run_tts(
            queue_tts=self.queue_tts,
            language=self.cfg.target_language_code,
            uuid=self.uuid,
            tts_type=self.cfg.tts_type,
            is_cuda=self.cfg.is_cuda
        )
        # 为每条字幕保留原始配音片段
        if settings.get('save_segment_audio', False):
            outname = self.cfg.target_dir + f'/segment_audio_{self.cfg.noextname}'
            Path(outname).mkdir(parents=True, exist_ok=True)
            for it in self.queue_tts:
                text = re.sub(r'["\'*?\\/|:<>\r\n\t]+', '', it['text'], flags=re.I | re.S)
                name = f'{outname}/{it["line"]}-{text[:60]}.wav'
                if Path(it['filename']).exists():
                    shutil.copy2(it['filename'], name)

    # 多线程实现裁剪参考音频
    def _create_ref_from_vocal(self):
        # 保底原始音频用于克隆时参考音频
        vocal = self.cfg.source_wav
        if self.clone_ref and Path(self.clone_ref).exists():
            # 人声背景声分离 出来的人声音频，44.1k，如果有降噪，则为 16000 
            vocal=self.clone_ref
        else:
            # 无则从原始视频中提取44.1k音频作为参考音频
            try:
                tmpfile = self.cfg.cache_folder + "/clone_ref_44100.wav"
                runffmpeg([
                    "-y",
                    "-i",
                    self.cfg.name,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "44100",
                    "-c:a",
                    "pcm_s16le",
                    tmpfile
                ])
                vocal=tmpfile
            except Exception as e:
                logger.exception(f'克隆语音前分离出 44.1k 的原始音频失败',exc_info=True)
            
        logger.debug(f'语音克隆模式下，所用参考音频为:{vocal}')
        # 裁切对应片段为参考音频
        def _cutaudio_from_vocal(it):
            try:
                logger.debug(f"裁切对应片段为参考音频：{it['startraw']}->{it['endraw']}\n当前{it=}")
                cut_from_audio(
                    audio_file=vocal,
                    ss=it['startraw'],
                    to=it['endraw'],
                    out_file=it['ref_wav']
                )
            except Exception as e:
                logger.exception(f'裁切参考音频失败:{it=},{e}', exc_info=True)

        all_task = []
        with ThreadPoolExecutor(max_workers=min(8, len(self.queue_tts), os.cpu_count())) as pool:
            for item in self.queue_tts:
                if item.get('ref_wav'):
                    all_task.append(pool.submit(_cutaudio_from_vocal, item))
            if len(all_task) > 0:
                _ = [i.result() for i in all_task]

    # 添加手动上传的额外背景音乐
    def _back_music(self) -> None:
        if self._exit() or not self.should_dubbing or not vail_file(self.cfg.target_wav) or not vail_file( self.cfg.background_music):
            return
        try:
            self.signal(text=tr("Adding background audio"))
            # 获取视频长度
            vtime = get_audio_time(self.cfg.target_wav)
            # 获取背景音频长度
            atime = get_audio_time(self.cfg.background_music)
            if atime < 1:
                return
            bgm_file = self.cfg.cache_folder + f'/bgm_file.wav'
            self.convert_to_wav(self.cfg.background_music, bgm_file)
            self.cfg.background_music = bgm_file
            beishu = math.ceil(vtime / atime)
            if self.cfg.loop_backaudio and beishu > 1 and vtime - 1000 > atime:
                # 获取延长片段
                file_list = [self.cfg.background_music for n in range(beishu + 1)]
                concat_txt = self.cfg.cache_folder + f'/{time.time()}.txt'
                create_concat_txt(file_list, concat_txt=concat_txt)
                concat_multi_audio(
                    concat_txt=concat_txt,
                    out=self.cfg.cache_folder + "/bgm_file_extend.wav")
                self.cfg.background_music = self.cfg.cache_folder + "/bgm_file_extend.wav"

            # 背景音频和配音合并
            cmd = ['-y',
                   '-i', os.path.basename(self.cfg.target_wav),
                   '-i', self.cfg.background_music,
                   '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
                   '-ac', '2',
                   '-c:a', 'pcm_s16le',
                   "lastend.wav"
                   ]
            runffmpeg(cmd, cmd_dir=self.cfg.cache_folder)
            self.cfg.target_wav = self.cfg.cache_folder + f"/lastend.wav"
        except Exception as e:
            logger.exception(f'添加背景音乐失败,静默跳过 {e}', exc_info=True)

    # 重新嵌回分离出的背景声音
    def _separate(self) -> None:
        # 如果背景音频分离失败，则静默返回
        if self._exit() or not self.cfg.embed_bgm or not vail_file(self.cfg.instrument) or not vail_file(self.cfg.target_wav):
            return
        try:
            self.signal(text=tr("Re-embedded background sounds"))
            vtime = get_audio_time(self.cfg.target_wav)
            atime = get_audio_time(self.cfg.instrument)
            if atime < 1:
                return
            beishu = math.ceil(vtime / atime)

            instrument_file = self.cfg.instrument
            logger.debug(f'合并背景音 {beishu=},{atime=},{vtime=}')
            if atime + 1000 < vtime:
                if int(self.cfg.loop_backaudio) == 1:
                    # 背景音通过循环方式延长
                    file_list = [instrument_file for n in range(beishu + 1)]
                    concat_txt = self.cfg.cache_folder + f'/{time.time()}.txt'
                    create_concat_txt(file_list, concat_txt=concat_txt)
                    concat_multi_audio(concat_txt=concat_txt,
                                             out=self.cfg.cache_folder + "/instrument-concat.wav")
                else:
                    # 通过变速延长背景音
                    change_speed_rubberband(instrument_file, self.cfg.cache_folder + f"/instrument-concat.wav",
                                                  vtime)
                instrument_file = self.cfg.cache_folder + f"/instrument-concat.wav"

            tmp_out_wav = Path(self.cfg.cache_folder + f'/{time.time()}-1.wav').as_posix()
            tmp_volume = Path(self.cfg.cache_folder + f'/{time.time()}.wav').as_posix()
            # 背景音量降低
            self.convert_to_wav(instrument_file, tmp_volume, ["-filter:a", f"volume={self.cfg.backaudio_volume}"])
            runffmpeg(['-y', '-i', os.path.basename(self.cfg.target_wav), '-i', os.path.basename(tmp_volume),
                             '-filter_complex',
                             "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', "-b:a", "128k",
                             '-c:a', 'pcm_s16le', os.path.basename(tmp_out_wav)], cmd_dir=self.cfg.cache_folder)
            shutil.copy2(tmp_out_wav, self.cfg.target_wav)
        except Exception as e:
            logger.exception(f'重新嵌入分离的背景音失败 {e}', exc_info=True)

    # 处理所需字幕
    def _process_subtitles(self) -> Union[tuple[str, str], None]:
        logger.debug(f"\n======准备要嵌入的字幕:{self.cfg.subtitle_type=}=====")
        if not Path(self.cfg.target_sub).exists() :
            raise VideoTransError(tr("No valid subtitle file exists")+self.cfg.target_sub)

        # 如果原始语言和目标语言相同，或不存原始语言字幕，则强制单字幕
        if not Path(self.cfg.source_sub).exists() or (self.cfg.source_language_code == self.cfg.target_language_code):
            if self.cfg.subtitle_type == 3:
                self.cfg.subtitle_type = 1
            elif self.cfg.subtitle_type == 4:
                self.cfg.subtitle_type = 2

        process_end_subtitle = self.cfg.cache_folder + f'/end.srt'
        # 单行字符数
        maxlen = int(
            settings.get('cjk_len', 15) if self.cfg.target_language_code[:2] in contants.CJK_LANG else
            settings.get('other_len', 60))
        target_sub_list = get_subtitle_from_srt(self.cfg.target_sub)

        srt_string = ""
        # 双硬字幕时的两种语言字幕分割符，用于定义不同样式
        _join_flag = ''
        # 双硬 双软字幕组装
        if self.cfg.subtitle_type in [3, 4]:
            source_sub_list = get_subtitle_from_srt(self.cfg.source_sub)
            source_length = len(source_sub_list)
            # 原语言单行字符长度
            source_maxlen = int(
                settings.get('cjk_len', 15) if self.cfg.source_language_code[:2] in ["zh", "ja", "jp", "ko",
                                                                                     'yu'] else
                settings.get('other_len', 60))

            # 双语字幕
            # 判断 双硬字幕 and 存在 ass.json 文件 and  (Bottom_Fontsize != Fontsize or PrimaryColour!=Bottom_PrimaryColour) 需要 对双语字幕的第2行设置不同颜色和尺寸
            _join_flag = self._get_join_flag()

            for i, it in enumerate(target_sub_list):
                # 换行
                _text = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n"
                if source_length > 0 and i < source_length:
                    _text_source = simple_wrap(source_sub_list[i]['text'], source_maxlen,
                                                     self.cfg.source_language_code)
                    _text = f'{_text_source}\n{_join_flag}{_text}' if self.cfg.output_srt == 1 else f'{_text}\n{_join_flag}{_text_source}'
                srt_string += f"{_text}\n\n"
            srt_string = srt_string.strip()
            process_end_subtitle = f"{self.cfg.cache_folder}/shuang.srt"
            Path(process_end_subtitle).write_text(srt_string, encoding='utf-8')
            Path(self.cfg.target_dir + "/shuang.srt").write_text(
                srt_string.replace('###', '') if _join_flag == '###' else srt_string, encoding='utf-8')
        else:
            # 单字幕，需处理字符数换行
            for i, it in enumerate(target_sub_list):
                tmp = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)

        # 目标字幕语言
        subtitle_langcode = translator.get_subtitle_code(show_target=self.cfg.target_language)
        logger.debug(
            f'最终确定字幕嵌入类型:{self.cfg.subtitle_type} ,目标字幕语言:{subtitle_langcode}, 字幕文件:{process_end_subtitle}\n')
        # 单软 或双软
        if self.cfg.subtitle_type in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        # 硬字幕转为ass格式 并设置样式
        process_end_subtitle_ass = set_ass_font(process_end_subtitle)
        basename = os.path.basename(process_end_subtitle_ass)
        return basename, subtitle_langcode

    def _get_join_flag(self):
        _join_flag = ""
        if self.cfg.subtitle_type != 3 or not Path(f'{ROOT_DIR}/videotrans/ass.json').exists():
            return _join_flag
        try:
            assjson = json.loads(Path(f'{ROOT_DIR}/videotrans/ass.json').read_text(encoding='utf-8'))
        except Exception:
            logger.warning(f'未自定义样式 ass.json ，忽略')
            return _join_flag
        else:
            for k, v in assjson.items():
                if k.startswith('Bottom_') and v != assjson.get(k[7:]):
                    _join_flag = '###'
                    break
        return _join_flag

    # 视频定格最后一帧延长末端
    def _video_extend(self, duration_ms=1000):
        sec = duration_ms / 1000.0
        final_video_path = Path(f'{self.cfg.cache_folder}/final_video_with_freeze_lastend.mp4').as_posix()
               
        cmd = ['-y', '-i', os.path.basename(self.cfg.novoice_mp4),
               '-vf', f'tpad=stop_mode=clone:stop_duration={sec:.3f}',
               '-c:v', 'libx264',
               '-crf', f'{settings.get("crf", 23)}',
               '-preset', settings.get('preset', 'veryfast'),
               '-an', 'final_video_with_freeze_lastend.mp4'
        ]
        try:
            runffmpeg(cmd, force_cpu=True, cmd_dir=self.cfg.cache_folder)
            if Path(final_video_path).exists():
                shutil.copy2(final_video_path, self.cfg.novoice_mp4)
                logger.debug(f"视频定格应延长{duration_ms}ms，实际向上取整秒延长{sec}s,操作成功。")
        except Exception as e:
            logger.exception(f"视频定格延长操作失败,跳过 {e}", exc_info=True)

    # 最终合成视频
    # 各个播放器对长短不一的音视频流处理态度截然不同
    # 为了保证任何平台都能100% 正常播放，先对音频或视频末尾做添加静音或定格预先对齐，再用 -shortest 明确砍齐
    # 无损输出时不对齐流，直接 -shortest 砍掉，防止重新编码导致有损
    def _join_video_audio_srt(self) -> None:
        if self._exit() or not self.should_hebing:
            return

        # 判断 novoice_mp4 是否完成
        is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
        if not Path(self.cfg.novoice_mp4).exists():
            raise VideoTransError(f'{self.cfg.novoice_mp4} 不存在')

        # 需要配音但没有配音文件
        if self.should_dubbing and not vail_file(self.cfg.target_wav):
            raise VideoTransError(f"{tr('Dubbing')}{tr('anerror')}:{self.cfg.target_wav}")

        self.precent = min(max(90, self.precent), 98)

        # 最终需嵌入视频的音频，可能是配音后文件，也可能是原始音频(未配音)
        target_m4a = self.cfg.cache_folder + "/will_embed.m4a"
        # 用于判断输出原始音频是否结束，is True是结束，
        output_source_output = True
        # 视频时长
        duration_ms = int(get_video_duration(self.cfg.novoice_mp4))
        # 如果视频时长大于音频时长，音频末尾加静音
        if not self.should_dubbing:
            # 无配音的使用原始音频
            self._get_origin_audio(target_m4a,duration_ms)
        else:
            # 单独输出一个高质量 原始音频输出到目标目录，单独线程执行，不影响继续运行
            output_source_output = False
            cmd = [
                "-y",
                "-i",
                self.cfg.name,
                "-vn",
                "-b:a", "128k",
                "-c:a",
                "aac",
                self.cfg.source_wav_output
            ]

            def _output():
                nonlocal output_source_output
                try:
                    runffmpeg(cmd)
                except Exception as e:
                    logger.exception(f'单独输出原始视频中音频文件到目标文件夹失败，跳过{e}', exc_info=True)
                finally:
                    output_source_output = True
            threading.Thread(target=_output, daemon=True).start()


            # 手动添加的背景音乐嵌入
            self._back_music()
            # 重新嵌入分离出的背景音
            self._separate()

            # 获取音频时长
            audio_ms = get_audio_time(self.cfg.target_wav)
            _cmd=[
                "-y",
                "-i",
                os.path.basename(self.cfg.target_wav)
            ]
            v_a_offset=duration_ms-audio_ms
            # 视频时长大于音频超100ms，加静音
            if v_a_offset>100:
                logger.debug(f'视频时长{duration_ms}ms-音频时长{audio_ms}ms={v_a_offset}ms,需延长音频')
                _cmd.extend(['-af', f'apad=pad_dur={v_a_offset/1000.0}'])
            _cmd.extend([
                "-ac", "2", "-b:a", "128k", "-c:a", "aac",
                os.path.basename(target_m4a)
            ])
            runffmpeg(_cmd, cmd_dir=self.cfg.cache_folder)

        shutil.copy2(target_m4a, self.cfg.target_wav_output)
        self.precent = min(max(95, self.precent), 98)
        # 输出视频格式
        _video_output_ext = settings.get('out_video_ext', '.mp4')
        # 处理所需字幕
        subtitles_file, subtitle_langcode = None, None
        if self.cfg.subtitle_type > 0:
            subtitles_file, subtitle_langcode = self._process_subtitles()

        if _video_output_ext!='.mp4':
            subtitle_langcode=translator.get_mkv_code(subtitle_langcode)

        # 字幕嵌入时进入视频目录下
        os.chdir(self.cfg.cache_folder)

        
        # 再次获取处理好末尾的音频真实时长
        audio_ms = get_audio_time(target_m4a)
        # 音频时长 - 视频时长差值 >0 则需要定格视频末尾
        a_v_offset=audio_ms-duration_ms

        
        # 如果需要输出的视频是 264 编码，则使用 -c:v copy,因开始和中间编码均为264，可以考虑使用copy (如果无硬字幕嵌入的话)
        is_copy_mode = str(self.video_codec_num) == '264'
        # 如果原始视频是标准264,需要输出也是264，未视频慢速，未嵌入硬字幕，则放弃视频末尾定格处理，以便实现无损输出
        is_lossless=self.is_copy_video and is_copy_mode and not self.cfg.video_autorate and self.cfg.subtitle_type not in [1, 3]
        if is_lossless:
            logger.debug(f'当前原始视频是标准264,输出也是264，未视频慢速，未嵌入硬字幕，放弃视频末尾处理，实现无损输出。音频时长-视频时长={a_v_offset}ms'+('，\n音频时长大于视频时长{a_v_offset}ms，理论上视频末尾应定格等待音频播放完毕，但不同播放器可能有不同处理方式，如音频截断，视频末尾黑屏等' if a_v_offset>0 else ''))
        
        # 音频长于视频>500ms才开始末尾定格
        elif a_v_offset > 500:
            try:
                self._video_extend(a_v_offset)
            except Exception as e:
                logger.exception(f'定格视频最后一帧时失败，跳过 {e}', exc_info=True)

        # 将生成的视频先导出到临时目录，防止包含各种奇怪符号的targetdir_mp4导致ffmpeg失败
        tmp_target_mp4 = self.cfg.cache_folder + f"/laste_target{_video_output_ext}"
        self.signal(text=tr("Video + Subtitles + Dubbing in merge"))

        try:
            protxt = self.cfg.cache_folder + f"/compose{time.time()}.txt"
            protxt_basename = os.path.basename(protxt)
            threading.Thread(target=self._hebing_pro, args=(protxt,), daemon=True).start()

            novoice_mp4_basename = os.path.basename(self.cfg.novoice_mp4)
            target_m4a_basename = os.path.basename(target_m4a)
            tmp_target_mp4_basename = os.path.basename(tmp_target_mp4)

            # 获取可用的硬件
            if not app_cfg.video_codec:
                app_cfg.video_codec = get_video_codec()

            cmd0 = [
                "-y",
                "-progress",
                protxt_basename
            ]

            cmd1 = [
                "-i",
                novoice_mp4_basename,
                "-i",
                target_m4a_basename
            ]
            enc_qua = ['-crf', f'{settings.get("crf", 23)}', '-preset', settings.get('preset', 'medium')]
            
            # 若选 cfr，无论是否有视频慢速，均固定帧率输出
            # 若选vfr仅在有视频慢速时使用，其他使用ffmpeg默认auto
            fps_mode=None
            if settings.get('fps_mode')=='cfr':
                fps_mode=["-r",f"{self.video_info['video_fps']}","-fps_mode","cfr"]
            elif self.cfg.video_autorate:
                fps_mode=["-fps_mode","vfr"]
            # 无字幕 或 软字幕
            if self.cfg.subtitle_type not in [1, 3]:
                # 软字幕
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend(["-i", subtitles_file])
                cmd1.extend([
                    '-map',
                    '0:v',
                    '-map',
                    '1:a'
                ])
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend(['-map', '2:s'])

                cmd1.extend([
                    "-c:v",
                    "copy"  if is_copy_mode else f"libx{self.video_codec_num}",
                    "-c:a",
                    "copy",
                ])
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend([
                        "-c:s",
                        "mov_text" if _video_output_ext == '.mp4' else 'srt',
                        "-metadata:s:s:0",
                        f"language={subtitle_langcode}"
                    ])

                cmd2 = [
                    "-movflags",
                    "+faststart",
                ]
                if fps_mode:
                    cmd2.extend(fps_mode)
                
                #"-t", str(duration_s),
                cmd2.extend(['-shortest',tmp_target_mp4_basename])
                if is_copy_mode:
                    logger.debug(f'[最终视频合成]copy模式，无需重新编码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)
                elif app_cfg.video_codec.startswith('libx') or settings.get('force_lib'):
                    # 不支持硬件编码的就无需尝试硬件了
                    logger.debug(f'[最终视频合成]不支持硬件编码或指定了强制软编解码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + enc_qua + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)
                else:
                    # 尝试使用硬件编解码
                    hw_decode_args, _, vcodec, enc_args = self._get_hard_cfg()
                    cmd1[cmd1.index('-c:v') + 1] = vcodec
                    # 如果硬件处理失败，回退软编
                    try:
                        self._subprocess(cmd0 + hw_decode_args + cmd1 + enc_args + cmd2)
                    except Exception as e:
                        cmd1[cmd1.index('-c:v') + 1] = f'libx{self.video_codec_num}'
                        logger.exception(f'硬件处理视频合成失败，回退软编 {e}', exc_info=True)
                        runffmpeg(cmd0 + cmd1 + enc_qua + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)

            # 硬字幕
            else:
                cmd1.append('-filter_complex')
                subtitle_filter = [f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"]
                cmd2 = [
                    "-map",
                    "[v_out]",
                    "-map",
                    "1:a",
                    "-c:v",
                    f'libx{self.video_codec_num}',
                    '-c:a',
                    'copy',
                ]
                cmd3 = ["-movflags", "+faststart"]

                if fps_mode:
                    cmd3.extend(fps_mode)
                #"-t", str(duration_s),
                cmd3.extend(['-shortest', tmp_target_mp4_basename])
                if app_cfg.video_codec.startswith('libx') or settings.get('force_lib'):
                    logger.debug(f'[最终视频合成]不支持硬件编解码或指定了强制软编解码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + subtitle_filter + cmd2 + enc_qua + cmd3,
                                    cmd_dir=self.cfg.cache_folder, force_cpu=True)
                else:
                    # 如果硬件处理失败，回退软编
                    try:
                        hw_decode_args, vf_string, vcodec, enc_args = self._get_hard_cfg(subtitles_file)
                        cmd2[cmd2.index('-c:v') + 1] = vcodec
                        self._subprocess(cmd0 + hw_decode_args + cmd1 + [vf_string] + cmd2 + enc_args + cmd3)
                    except Exception as e:
                        cmd2[cmd2.index('-c:v') + 1] = f'libx{self.video_codec_num}'
                        logger.exception(f'硬件处理视频合成失败，回退软编 {e}', exc_info=True)
                        runffmpeg(cmd0 + cmd1 + subtitle_filter + cmd2 + enc_qua + cmd3,
                                        cmd_dir=self.cfg.cache_folder, force_cpu=True)
        except Exception as e:
            raise VideoTransError(tr('Error in embedding the final step of the subtitle dubbing')+str(e)) from e
        finally:
            os.chdir(ROOT_DIR)

        # 复制到目标文件夹
        if Path(tmp_target_mp4).exists():
            try:
                shutil.copy2(tmp_target_mp4, self.cfg.targetdir_mp4[:-4]+_video_output_ext)
            except Exception:
                # 如果移动失败，则尝试直接复制为 0.mp4 or 0.mkv
                try:
                    shutil.copy2(tmp_target_mp4, f'{self.cfg.target_dir}/0{_video_output_ext}')
                except Exception as e:
                    logger.exception(f'再次复制到目标文件夹内 0{_video_output_ext}也失败 {e}', exc_info=True)
                    raise VideoTransError(tr('Translation successful but transfer failed.', tmp_target_mp4)) from e

        # 有可能输出原始音频到目标文件夹的程序仍在执行，但不影响
        while output_source_output is not True:
            if app_cfg.exit_soft:return
            time.sleep(1)
        return

    def _get_origin_audio(self, output,duration_ms=0):
        # 无需配音的场景下取出原始音频
        if self.video_info.get('streams_audio', 0) == 0:
            # 无音频流
            return
        cmd = [
            "-y",
            "-i",
            self.cfg.name,
            "-vn"
        ]
        # 如果视频时长大于音频 100ms，需延长
        v_a_offset=int(self.video_info['time'])-duration_ms
        if duration_ms>0 and v_a_offset>100:
            cmd.extend(['-af', f'apad=pad_dur={v_a_offset/1000.0}'])
            
        cmd.extend(['-c:a', 'aac', '-b:a', '128k',output])
        return runffmpeg(cmd)

    # ffmpeg进度日志
    def _hebing_pro(self, protxt) -> None:
        while 1:
            if app_cfg.exit_soft or self.hasend or self.uuid in app_cfg.stoped_uuid_set: return
            content = read_last_n_lines(protxt)
            if not content:
                time.sleep(0.5)
                continue

            if content[-1] == 'progress=end':
                return
            idx = len(content) - 1
            end_time = "00:00:00"
            while idx > 0:
                if content[idx].startswith('out_time='):
                    end_time = content[idx].split('=')[1].strip()
                    break
                idx -= 1
            self.signal(text=tr('kaishihebing') + f' {end_time}')
            time.sleep(0.5)

    # 视频合成时，返回可用的硬件解码参数、字幕嵌入参数、视频编码参数、质量相关参数
    def _get_hard_cfg(self, subtitles_file=None, codec=None):
        os_name = platform.system()
        if not app_cfg.video_codec:
            app_cfg.video_codec = get_video_codec()
        # 仅用于确定编码器部分，具体 264或265由 codec 决定
        hw_type = app_cfg.video_codec
        logger.debug(f'原始{hw_type=}')

        if '_' in hw_type:
            _hw_type_list = hw_type.lower().split('_')
            if _hw_type_list[0] == 'vaapi':
                hw_type = 'vaapi'
            else:
                hw_type = _hw_type_list[1]

        logger.debug(f'整理后{hw_type=}')

        # 硬字幕由于是软过滤，必须先在内存中压制。
        # 不同的硬件编码器可能需要在软过滤后，将画面重新上传到显存（hwupload）
        codec = f'{self.video_codec_num}' if not codec else codec
        vcodec = f"libx{codec}"
        _crf = f'{settings.get("crf", 23)}'

        # 全局参数，硬件解码相关
        global_args = []
        # 硬字幕嵌入参数，软字幕忽略
        vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

        # 硬件兼容有限，防止出错
        _preset = settings.get('preset', 'medium')
        if 'fast' in _preset:
            _preset = 'fast'
        elif 'slow' in _preset:
            _preset = 'slow'

        if _preset not in ['fast', 'slow', 'medium']:
            _preset = 'medium'
        enc_args = ['-crf', _crf, '-preset', _preset]

        # --- 参数映射表 ---
        PRESET_MAP = {
            # NVENC: p1 (最快) - p7 (最慢/质量最好)
            'nvenc': {'fast': 'p2', 'medium': 'p4', 'slow': 'p7'},
            # QSV: veryfast, faster, fast, medium, slow, slower, veryslow
            'qsv': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
            # AMF: speed, balanced, quality
            'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
            # VAAPI: 通常也接受 standard presets
            'vaapi': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
            # VideoToolbox: 通常不支持 -preset 参数，留空以跳过处理
            'videotoolbox': None
        }

        # --- Nvidia (NVENC) ---
        if hw_type in ['nvenc']:
            vcodec = "h264_nvenc" if codec == '264' else "hevc_nvenc"
            # nvenc 使用 -cq (Constant Quality) 替代 crf，p4 预设在速度和质量间平衡较好
            enc_args = ['-cq', _crf, '-preset', PRESET_MAP.get('nvenc').get(_preset, 'p4')]
            # 优先硬件解码
            if settings.get('hw_decode'):
                global_args = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
                vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',hwupload_cuda[v_out]"
            else:
                vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

            return global_args, vf_string, vcodec, enc_args
        # --- Mac (VideoToolbox) ---
        if hw_type in ['videotoolbox']:
            vcodec = "h264_videotoolbox" if codec == '264' else "hevc_videotoolbox"
            # videotoolbox 质量控制，通常用 -q:v (范围约在 40-60 之间视觉无损)
            quality = int(100 - (int(_crf) * 1.4))
            enc_args = ['-q:v', f'{int(max(1, min(quality, 100)))}']
            return global_args, vf_string, vcodec, enc_args

        # --- Intel (QSV) & AMD (AMF) ---
        if hw_type in ['qsv', 'amf', 'vaapi']:
            if os_name == 'Linux':
                # 【Linux 特殊处理】
                # 在 Linux 下，Intel 和 AMD 开源驱动通常统一走 VAAPI 接口
                devices = glob.glob('/dev/dri/renderD*')
                device = devices[0] if devices else '/dev/dri/renderD128'
                if settings.get('hw_decode'):
                    global_args = ['-hwaccel', 'vaapi', '-hwaccel_device', device, '-hwaccel_output_format', 'vaapi']
                    vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                else:
                    global_args = [
                        '-init_hw_device', f'vaapi=vaapi:{device}'
                    ]
                    vf_string = f"[0:v]subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                vcodec = "h264_vaapi" if codec == '264' else "hevc_vaapi"
                enc_args = ['-qp', _crf, '-preset', PRESET_MAP.get('vaapi').get(_preset, 'medium')]
                return global_args, vf_string, vcodec, enc_args
                # VAAPI 要求在软滤镜（字幕）处理完后，转换像素格式并上传到显存

            # Windows 环境
            if hw_type in ['qsv']:
                vcodec = "h264_qsv" if codec == '264' else "hevc_qsv"
                # QSV 使用 ICQ 模式 (Intelligent Constant Quality)
                enc_args = ['-global_quality', _crf, '-preset', PRESET_MAP.get('qsv').get(_preset, 'medium')]
            else:
                vcodec = "h264_amf" if codec == '264' else "hevc_amf"
                # AMF 使用恒定质量参数 (CQP)
                enc_args = ['-rc', 'cqp', '-qp_p', _crf, '-qp_i', _crf, '-quality',
                            PRESET_MAP.get('amf').get(_preset, 'balanced')]
            return global_args, vf_string, vcodec, enc_args

        return global_args, vf_string, vcodec, enc_args

    def _subprocess(self, cmd):
        logger.debug(f'[尝试硬件编解码执行命令]\n{" ".join(cmd)}\n')
        try:
            if app_cfg.exit_soft: return
            cmd = ["ffmpeg", '-nostdin'] + cmd
            subprocess.run(
                cmd,
                # stdout=subprocess.PIPE,
                # stderr=subprocess.PIPE,
                encoding="utf-8",
                errors='ignore',
                check=True,
                text=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=self.cfg.cache_folder
            )
            return True
        except subprocess.CalledProcessError as e:
            raise FFmpegError(f"尝试使用硬件执行命令出错[CalledProcessError]:{e.stderr}\n{e.stdout},{e}") from e
