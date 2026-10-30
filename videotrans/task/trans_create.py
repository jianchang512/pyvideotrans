import time
import threading, shutil
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List, Dict

from videotrans.configure.config import tr, app_cfg, settings, logger
from videotrans.configure import config
from videotrans.translator import get_audio_code, LLM_CONCERT_DICT, AI_TRANS_CHANNELS, HYMT2_INDEX
from videotrans.task._base import BaseTask
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.configure import constants

from videotrans.task._stage_prepare import PrepareMixin
from videotrans.task._stage_recogn import RecognMixin
from videotrans.task._stage_diariz import DiarizMixin
from videotrans.task._stage_translate import TranslateMixin
from videotrans.task._stage_dubbing import DubbingMixin
from videotrans.task._stage_align import AlignMixin
from videotrans.task._stage_audio import AudioMixin
from videotrans.task._stage_subtitle import SubtitleMixin
from videotrans.task._stage_assemble import AssembleMixin

# 视频翻译完整流程
@dataclass
class TransCreate(
    AssembleMixin,
    SubtitleMixin,
    AudioMixin,
    AlignMixin,
    DubbingMixin,
    TranslateMixin,
    DiarizMixin,
    RecognMixin,
    PrepareMixin,
    BaseTask,
):
    # 配置信息
    cfg: TaskCfgVTT = field(default_factory=TaskCfgVTT, repr=False)
    # 存放识别出的原始字幕
    source_srt_list: List = field(default_factory=list)
    # 存放目标语言字幕
    target_srt_list: List = field(default_factory=list)
    # 原始视频时长
    video_time: float = 0.0
    # 原始视频信息
    video_info: Dict = field(default_factory=dict, repr=False)
    # 视频数据流复制
    is_copy_video: bool = False
    # 输出视频所用编码
    video_codec_num: int = 264
    ignore_align: bool = False
    # 原始输入是音频文件
    is_audio_trans: bool = False
    # 存放待配音字幕队列
    queue_tts: List = field(default_factory=list, repr=False)
    # 用于克隆的参考音频，降噪、人声背景分离后设置
    clone_ref: str = ""
    # 二次识别
    should_recogn2: bool = False
    # 批量时不进行说话人分离，仅在单个视频翻译时，根据选项进入说话人
    # 只要 do_diarize 是 Flase，无论是否选中分离说话人，都不分离，是 True时，若选中则分离
    do_diarize: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not self.cfg.cache_folder:
            self.cfg.cache_folder = f"{config.TEMP_DIR}/{self.uuid}"
        if self.cfg.clear_cache:
            if self.cfg.target_dir and Path(self.cfg.target_dir).is_dir():
                shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
            if self.cfg.cache_folder and Path(self.cfg.cache_folder).is_dir():
                shutil.rmtree(self.cfg.cache_folder, ignore_errors=True)

        self.signal(text=tr('kaishichuli'))
        self.max_speakers = max(self.cfg.nums_diariz, 0) if self.cfg.enable_diariz else -1
        if self.max_speakers > 0:
            self.max_speakers += 1
        self.should_recogn = True
        self.video_codec_num = int(settings.get('video_codec', 264))

        self.cfg.detect_language = get_audio_code(show_source=self.cfg.source_language_code)

        self.cfg.novoice_mp4 = f"{self.cfg.cache_folder}/novoice.mp4"

        self.cfg.source_sub = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt"
        self.cfg.source_wav_output = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.m4a"
        self.cfg.source_wav = f"{self.cfg.cache_folder}/{self.cfg.source_language_code}.wav"

        self.cfg.target_sub = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt"
        self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.m4a"
        self.cfg.target_wav = f"{self.cfg.cache_folder}/target.wav"

        self.cfg.targetdir_mp4 = f"{self.cfg.target_dir}/{self.cfg.noextname}.mp4"

        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.target_language_code:
            self.should_dubbing = True

        if self.cfg.app_mode != 'tiqu' and (self.should_dubbing or self.cfg.subtitle_type > 0):
            self.should_hebing = True

        if self.cfg.target_language_code and self.cfg.target_language_code != self.cfg.source_language_code:
            self.should_trans = True

        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.source_language_code == self.cfg.target_language_code:
            self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}-dubbing.m4a"
            self.cfg.target_wav = f"{self.cfg.cache_folder}/target-dubbing.wav"
            self.should_dubbing = True

        if self.cfg.ext in constants.AUDIO_EXITS:
            self.is_audio_trans = True
            self.should_hebing = False

        if not self.cfg.target_language_code:
            self.should_dubbing = False
            self.should_trans = False

        if self.cfg.voice_role == 'No':
            self.should_dubbing = False

        if self.cfg.app_mode == 'tiqu':
            self.cfg.enable_diariz = False
            self.should_dubbing = False
        self.should_recogn2 = self.cfg.recogn2pass and self.should_dubbing and self.cfg.subtitle_type < 3 and (
                self.cfg.source_language_code != self.cfg.target_language_code)

        self.cfg.vocal = f"{self.cfg.cache_folder}/vocal.wav"
        self.cfg.instrument = f"{self.cfg.cache_folder}/instrument.wav"

        logger.debug(f"{self}")
        self.signal(text="forbid", type="disabled_edit")

        def runing():
            t = time.time()
            while not self.hasend:
                if self._exit(): return
                time.sleep(1)
                self.signal(text=f"{int(time.time() - t)}???{self.precent}", type="set_precent")

        if app_cfg.exec_mode != 'cli':
            threading.Thread(target=runing, daemon=True).start()

    # 输出详细配置，方便判断出错时问题所在
    def __repr__(self):
        _msg = []
        from videotrans.recognition import ALLOW_CHANGE_MODEL
        from videotrans.util.tools import get_recogn_type, get_tanslate_type, get_tts_type
        isTrue = {True: tr("Selected"), False: tr("Not-Selected")}
        _loops = [tr('The bgm briefly lengthens'), tr('loop the BGM')]
        _subtitles = [
            tr('nosubtitle'),
            tr('embedsubtitle'),
            tr('softsubtitle'),
            tr('embedsubtitle2'),
            tr('softsubtitle2')
        ]

        if self.cfg.app_mode == "tiqu":
            _msg.append(tr("Extract Srt And Translate"))
            if self.cfg.copysrt_rawvideo:
                _msg.append(f'{isTrue[True]} {tr("Moving subtitle")}')
            if self.cfg.output_srt > 0:
                _msg.append(tr('Target language under(Bilingual)') if self.cfg.output_srt == 1 else tr(
                    'Target language up(Bilingual)'))
        else:
            _msg.append(f'{tr("Standard Function Mode")} {"批量模式" if self.cfg.batch else "单视频模式"}')
            batch_num = int(float(settings.get('batch_nums', 0)))
            if self.cfg.batch and batch_num > 0:
                _msg.append(f'{tr("batch_nums_title")}:{batch_num}')

        _msg.append(
            f'{tr("Select file")}: {self.cfg.name}, \n{tr("Output directory")}: {self.cfg.target_dir},\n{self.cfg.cache_folder=}')
        _msg.append(
            f'{isTrue[self.cfg.clear_cache]} {tr("Del Generated")}, {isTrue[self.cfg.is_cuda]} {tr("Enable CUDA?")}')

        if self.cfg.remove_noise:
            _msg.append(f'{isTrue[True]} {tr("Noise reduction")},{tr("noise_model_title")}:{settings.get("noise_model")}')

        if self.cfg.fix_punc > 0:
            _msg.append(
                f'{isTrue[True]} {tr("Restore punctuation") if self.cfg.fix_punc == 1 else tr("Delete punctuation")}')
        if self.cfg.rephrase:
            ai_type = settings.get('llm_ai_type', 1)
            ai_dict=LLM_CONCERT_DICT[ai_type]
            _msg.append(f'{isTrue[True]} {tr("LLM Rephrase")},{tr("llm_chunk_size_title")}:{settings.get("llm_chunk_size")}, {tr("llm_ai_type_title")}: {ai_dict["name"]}')
            if settings.get('llm_resegment_title'):
                _msg.append(f'{isTrue[True]} {tr("llm_resegment_title")}')

        _msg.append(
            f"{tr('Speech Recognit')}:{get_recogn_type(self.cfg.recogn_type)}, {self.cfg.model_name if self.cfg.recogn_type in ALLOW_CHANGE_MODEL else ''}, {tr('Speech language')}: {self.cfg.source_language}")

        _msg.extend([
            f'{tr("max_speech_duration_s_title")}: {settings.get("max_speech_duration_s")}s',
            f'{tr("min_speech_duration_ms_title")}: {settings.get("min_speech_duration_ms")}ms',
            f'{tr("min_silence_duration_ms_title")}: {settings.get("min_silence_duration_ms")}ms',
            f'{tr("threshold_title")}: {settings.get("threshold")}',
            f'{tr("vad_type_title")}: {settings.get("vad_type")}',
        ])


        if self.cfg.recogn_type==0:
            _msg.append(f'{tr("cuda_com_type_title")}:{settings.get("cuda_com_type")}')
            _msg.append(f'{tr("beam_size_title")}:{settings.get("beam_size")}')
            _msg.append(f'{tr("best_of_title")}:{settings.get("best_of")}')
            _msg.append(f'{tr("condition_on_previous_text_title")}:{settings.get("condition_on_previous_text")}')
            _msg.append(f'{tr("repetition_penalty_title")}:{settings.get("repetition_penalty")}')
            _msg.append(f'{tr("compression_ratio_threshold_title")}:{settings.get("compression_ratio_threshold")}')

        if self.cfg.target_language in [None, 'No', '-'] or self.cfg.source_language == self.cfg.target_language:
            _msg.append(f'Dont translation subtitle: {self.cfg.source_language=},{self.cfg.target_language=}')
        else:
            _msg.append(f"{tr('Translate channel')}:{get_tanslate_type(self.cfg.translate_type)},{tr('Speech language')}:{self.cfg.source_language},{tr('Target lang')}:{self.cfg.target_language}")
            if self.cfg.translate_type in AI_TRANS_CHANNELS and self.cfg.translate_type != HYMT2_INDEX:
                _msg.append(f"{isTrue[settings['aisendsrt']]} {tr('Send SRT')}, {tr('aitrans_thread_title')}:{settings.get('aitrans_thread')}")
            else:
                _msg.append(f'{tr("trans_thread_title")}: {settings.get("trans_thread")}')


        if self.cfg.app_mode != 'tiqu':
            if self.cfg.voice_role in [None, 'No']:
                _msg.append(f'Dont dubbing: {self.cfg.voice_role=}')
            else:
                _msg.append(
                    f"{tr('Dubbing channel')}:{get_tts_type(self.cfg.tts_type)}, {tr('Dubbing role')}:{self.cfg.voice_role}, {tr('Target lang')}:{self.cfg.target_language}")
                _msg.append(
                    f'Volume:{self.cfg.volume}, Speed:{self.cfg.voice_rate}, {isTrue[self.cfg.voice_autorate]} {tr("Dubbing acceler")}, {isTrue[self.cfg.video_autorate]} {tr("Slow video")}')
                if not self.cfg.voice_autorate and not self.cfg.video_autorate:
                    _msg.append(
                        f'{isTrue[self.cfg.remove_silent_mid]} {tr("Del inline mute?")},  {isTrue[self.cfg.align_sub_audio]} {tr("Align subtitles and audio")}')

                _se, _all = settings.get('remove_dubb_silence', True), settings.get('remove_dubb_all_silence', True)
                if _se:
                    _msg.append(f'{isTrue[True]}  {tr("remove_dubb_silence_title")}')
                if _all:
                    _msg.append(f'{isTrue[True]}  {tr("remove_dubb_all_silence_title")}')
                if _se or _all:
                    _msg.append(
                        f"{tr('remove_dubb_silence_level_title')}: {settings.get('remove_dubb_silence_level', 'default')}")

                if self.cfg.recogn2pass:
                    _msg.extend([
                        f'{isTrue[True]}: {tr("STT again")}, {tr("model_for_recogn2_title")}: {settings.get("model_for_recogn2")}',
                        f'{tr("max_speech_duration_s2_title")}: {settings.get("max_speech_duration_s2")}s',
                        f'{tr("min_speech_duration_ms2_title")}: {settings.get("min_speech_duration_ms2")}ms',
                    ])
                    if self.cfg.subtitle_type > 2:
                        _msg.append(f'\t已选 {tr("STT again")} 但不会生效，因已选择 嵌入双字幕，需保证原始和目标字幕时间轴一致，而二次语音识别会重新生成时间轴不同的目标字幕]')

            if not self.cfg.batch and self.do_diarize and self.cfg.enable_diariz:
                _msg.append(
                    f'{isTrue[True]} {tr("Speaker classification")}: {tr("No limit") if self.cfg.nums_diariz < 1 else self.cfg.nums_diariz + 1}')
                _msg.append(f'{tr("speaker_type_title")}: {settings.get("speaker_type")}')

            _msg.append(f'{_subtitles[self.cfg.subtitle_type]}')
            if self.cfg.subtitle_type in [1,3]:
                _msg.append(f'{tr("cjk_len_title")}:{settings.get("cjk_len")}, {tr("other_len_title")}:{settings.get("other_len")}')

            _vocal_exists = self.cfg.vocal and Path(self.cfg.vocal).exists()
            _instr_exists = self.cfg.instrument and Path(self.cfg.instrument).exists()
            if self.cfg.is_separate or self.cfg.background_music or _vocal_exists or _instr_exists:
                _str = f"{isTrue[self.cfg.is_separate]} {tr('Retain original background sound')}"
                if self.cfg.is_separate:
                    _str += f", Model:{settings.get('uvr_models')}"
                if self.cfg.embed_bgm:
                    _str += f',{isTrue[True]} {tr("embed_bgm")}, {tr("backaudio_volume_title")}:{self.cfg.backaudio_volume}, {_loops[self.cfg.loop_backaudio]}'

                if self.cfg.background_music:
                    _str += f', {tr("Add background audio")}:{self.cfg.background_music}\n'
                if _vocal_exists:
                    _str += self.cfg.vocal
                if _instr_exists:
                    _str += self.cfg.instrument
                _msg.append(_str)
            if self.cfg.only_out_mp4:
                _msg.append(f"{isTrue[True]} {tr('Output only mp4')}")


        if self.video_time > 0:
            _msg.append(f'video duration:{self.video_time}ms')
        if self.video_info:
            _msg.append(f'video information:{self.video_info}')

        _msg.append(f'{self.cfg=}')
        return "\n".join(_msg)
