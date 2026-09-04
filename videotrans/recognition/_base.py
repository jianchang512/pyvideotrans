import re, time, os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from videotrans.configure.config import tr, settings, logger
from videotrans.configure import config
from videotrans.configure.base import BaseCon
from videotrans.configure.excepts import SpeechToTextError
from videotrans.task.taskcfg import SrtItem
from videotrans.configure import contants
from videotrans.util.help_srt import ms_to_time_string
from tenacity import RetryError


@dataclass
class BaseRecogn(BaseCon):
    # 语音识别类型
    recogn_type: int = 0
    # 语音转录时 字幕检测语言
    detect_language: str = ""
    # 模型名字
    model_name: Optional[str] = None
    # 待识别的 16k wav
    audio_file: Optional[str] = None
    # 临时目录
    cache_folder: Optional[str] = None
    # 任务id
    uuid: Optional[str] = None
    # 启用cuda加速
    is_cuda: bool = False
    # 字幕嵌入类型 0 1 2 3 4
    subtitle_type: int = 0
    # 是否已结束
    has_done: bool = field(default=False, init=False)
    # 错误消息
    error: str = field(default='', init=False)
    # 识别 api地址
    api_url: str = field(default='', init=False)
    # 设备类型 cpu cuda
    device: str = field(init=False, default='cpu')
    # 标点符号
    flag: List[str] = field(init=False, default_factory=list)
    # 存放返回的字幕列表
    raws: List = field(default_factory=list, init=False)
    # 文字之间连接，中日韩粤语高棉语泰语 直接相连，其他空格
    join_word_flag: str = field(init=False, default=' ')
    # 是否需转为简体中文
    jianfan: bool = False
    # 单行字幕字符数
    maxlen: int = 20
    audio_duration: int = 0
    # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量
    max_speakers: int = -1

    # vad切割好的数据
    speech_timestamps: List = field(default_factory=list)
    # 当前需进行的是否是二次识别
    recogn2pass: bool = False
    # 每次识别后等待时间，用于在线API，防止超频
    asr_wait: float = float(settings.get('asr_wait', 0))
    # 本地模型存放目录
    local_dir: str = None

    def __post_init__(self):
        super().__post_init__()
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 常见标点
        self.flag = contants.PUNC_FLAGS
        # 逗号等软性标点
        self.half_flag = contants.PUNC_FLAGS_HALF
        # 句子终止标点
        self.end_flag = contants.PUNC_FLAGS_END
        # 连接字符 中日韩粤语高棉语泰国语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "
        # 是中日韩文字
        self.is_cjk = False

        _lang = self.detect_language.split('-')[0].lower()
        if self.detect_language and _lang in contants.CJK_LANG:
            self.maxlen = int(float(settings.get('cjk_len', 20)))
            self.jianfan = True if _lang == 'zh' and settings.get('zh_hant_s') else False
            self.flag.append(" ")
            self.join_word_flag = ""
            self.is_cjk = True
        else:
            self.maxlen = int(float(settings.get('other_len', 60)))
            self.jianfan = False

    # run->_exec
    def run(self) -> Union[List[SrtItem], None]:
        try:
            if hasattr(self, '_download'):
                self.signal(text=tr("check or download models"))
                self._download()
            self.signal(text=tr("Transcription in progress, please wait"))
            res = self._exec()
            if not res:
                from videotrans.configure.excepts import SpeechToTextError
                raise SpeechToTextError(
                    tr('No speech was detected, please make sure there is human speech in the selected audio/video and that the language is the same as the selected one.'))
            if self.recogn2pass:
                return res
            return self._post_fix(res)
        except RetryError as e:
            raise e.last_attempt.exception()
        except (OSError, FileNotFoundError) as e:
            _e = str(e)
            if self.local_dir and ("no file named model.safetensors" in _e or os.path.basename(self.local_dir) in _e):
                from videotrans.configure.excepts import DownloadModelsError
                raise DownloadModelsError(tr('model incomplete error', self.local_dir, tr('Help document')))
            raise

    # 对转录结果进行简单后处理
    @staticmethod
    def _post_fix(res: List[SrtItem]) -> List[SrtItem]:
        srt_list = []
        for i, it in enumerate(res):
            text = it['text'].strip()
            if text and not re.match(contants.NON_WORD, text):
                it['line'] = len(srt_list) + 1
                srt_list.append(it)
            else:
                logger.warning(f'移除无效字幕行,全部由符号组成的行：{i=},{text=}')

        if not srt_list:
            return []

        for i, it in enumerate(srt_list):
            if i > 0 and srt_list[i - 1]['end_time'] > it['start_time']:
                logger.warning(
                    f'\n前面字幕[{i-1}] end_time > 当前字幕[{i}] start_time，重叠，需修正\n前{srt_list[i - 1]=}\n当{it=}\n')
                srt_list[i - 1]['end_time'] = it['start_time']
                srt_list[i - 1]['endraw'] = ms_to_time_string(ms=it['start_time'])
                srt_list[i - 1]['time'] = f"{srt_list[i - 1]['startraw']} --> {srt_list[i - 1]['endraw']}"


        if settings.get('del_end_punc'):
            logger.debug(f'开始移除每条字幕末尾标点')
            for it in srt_list:
                # 移除末尾标点
                it['text'] = it['text'].strip('。，？！,.?!').strip()
        return srt_list

    def _exec(self) -> Union[List[SrtItem], None]:
        raise NotImplemented()

    # 有些识别渠道需要预先使用VAD切割为合适时长的音频片段，然后再对片段识别，每个识别结果即为一条字幕
    # whisper模型并且没有选中预先分割，无需切割
    def _vad_split(self):
        _st = time.time()
        _vad_type = settings.get('vad_type', 'tenvad')
        self.signal(text=f'VAD:{_vad_type} split audio...')

        _min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 1000)
        # 最长片段不得大于25s,并且不得小于 _min_speech
        _max_speech = max(min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000), _min_speech + 1000)

        # 静音阈值不得低于100ms
        _min_silence = max(int(settings.get('min_silence_duration_ms', 600)), 100)


        kw = {
            "input_wav": self.audio_file,
            "threshold": float(settings.get('threshold', 0.45)),
            "min_speech_duration_ms": _min_speech,
            "max_speech_duration_ms": _max_speech,
            "min_silent_duration_ms": _min_silence
        }


        try:
            from videotrans.process.vad import get_speech_timestamp, get_speech_timestamp_silero
            self.speech_timestamps = get_speech_timestamp(
                **kw) if _vad_type == 'tenvad' else get_speech_timestamp_silero(**kw)
        except Exception as e:
            msg=f'[{_vad_type}]:{kw=}\n{e}'
            logger.exception(msg, exc_info=True)
            if not self.recogn2pass:
                raise SpeechToTextError(msg) from e
        self.signal(text=f'[VAD] ended {int(time.time() - _st)}s')

    # 预先使用 VAD 将待识别的音频切割为语句片段后进行识别
    def cut_audio(self) -> List[SrtItem]:
        from pydub import AudioSegment
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)

        if not self.speech_timestamps:
            self._vad_split()

        audio = AudioSegment.from_wav(self.audio_file)

        # 深拷贝
        segs = [seg[:] for seg in self.speech_timestamps]
        segs = [[max(0, s), max(0, e)] for s, e in segs if e > s]

        # 为每个片段添加 200ms 静音头尾并导出
        # 音频为 16k 单声道
        silent_segment = AudioSegment.silent(
            duration=400,
            frame_rate=audio.frame_rate
        ).set_channels(audio.channels).set_sample_width(audio.sample_width)

        data = []
        for i, (start_ms, end_ms) in enumerate(segs):
            startraw = ms_to_time_string(ms=start_ms)
            endraw = ms_to_time_string(ms=end_ms)
            file_name = f"{dir_name}/audio_{i}.wav"
            chunk = audio[start_ms:end_ms]
            final_audio = silent_segment + chunk + silent_segment
            final_audio.export(file_name, format="wav")
            data.append(SrtItem(
                line=i + 1,
                text="",
                start_time=start_ms,
                end_time=end_ms,
                startraw=startraw,
                endraw=endraw,
                time=f'{startraw} --> {endraw}',
                filename=file_name
            ))

        logger.debug(f'切分为 {len(data)} 个音频片段')
        return data
