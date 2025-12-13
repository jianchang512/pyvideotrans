import json,re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict,  Optional, Union

from tenacity import RetryError

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure.config import tr, logs
from videotrans.util import tools


@dataclass
class BaseRecogn(BaseCon):
    recogn_type: int = 0  # 语音识别类型
    # 字幕检测语言
    detect_language: str = None

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

    # 字幕嵌入类型 0 1234
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
    # 文字之间连接，中日韩粤语直接相连，其他空格
    join_word_flag: str = field(init=False, default=' ')
    # 是否需转为简体中文
    jianfan: bool = False
    # 字幕行字符数
    maxlen: int = 20
    split_type: int=0 #0 整体识别，1 均等分割
    max_speakers:int=-1 # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量

    def __post_init__(self):
        super().__post_init__()
        if not tools.vail_file(self.audio_file):
            raise RuntimeError(f'No {self.audio_file}')
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 断句标志
        self.flag = [",", ".", "?", "!", ";", "，", "。", "？", "；", "！"]
        # 连接字符 中日韩粤语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "

        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
            self.maxlen = int(float(config.settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings.get('zh_hant_s') else False
            self.flag.append(" ")
            self.join_word_flag = ""
        else:
            self.maxlen = int(float(config.settings.get('other_len', 60)))
            self.jianfan = False

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        try:
            srt_list=[]
            
            for i,it in enumerate(self._exec()):
                text=it['text'].strip()
                # 移除无效行
                if text and not re.match(r'^[,.?!;\'"_，。？；‘’“”！~@#￥%…&*（【】）｛｝《、》\$\(\)\[\]\{\}=+\<\>\s-]+$',text):
                    it['line']=len(srt_list)+1
                    srt_list.append(it)
            return srt_list
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            logs(str(e), level="except")
            raise

    def _exec(self) -> Union[List[Dict], None]:
        pass

    # 重新进行LLM断句，仅限 faster-whisper/openai-whisper渠道
    '''
    words数据格式
    words=[
        {
            "start": 1.92,
            "end": 2.16,
            "word": "\u4e94"
        },
        {
            "start": 2.16,
            "end": 2.32,
            "word": "\u8001"
        },
        ...
    ]
    '''
    def re_segment_sentences_json(self, words):
        try:
            from videotrans.translator._chatgpt import ChatGPT
            ob = ChatGPT()
            self._signal(text=tr("Re-segmenting..."))
            return ob.llm_segment(words, config.settings.get('llm_ai_type', 'openai'))
        except json.decoder.JSONDecodeError as e:
            self._signal(text=tr("Re-segmenting Error"))
            logs(f"重新断句失败[JSONDecodeError]，已恢复原样 {e}",level='warn')
            raise
        except Exception as e:
            self._signal(text=tr("Re-segmenting Error"))
            logs(f"重新断句失败[except]，已恢复原样 {e}",level='warn')
            raise

    # 不需要本地重新断句



    # 根据 时间开始结束点，切割音频片段,并保存为wav到临时目录，记录每个wav的绝对路径到list，然后返回该list
    def cut_audio(self):
        sampling_rate = 16000
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import (
            VadOptions,
            get_speech_timestamps
        )
        from pydub import AudioSegment
        import time

        def convert_to_milliseconds(timestamps):
            milliseconds_timestamps = []
            for timestamp in timestamps:
                milliseconds_timestamps.append(
                    {
                        "start": int(round(timestamp["start"] / sampling_rate * 1000)),
                        "end": int(round(timestamp["end"] / sampling_rate * 1000)),
                    }
                )

            return milliseconds_timestamps

        vad_p = {
            "threshold": float(config.settings.get('threshold',0.45)),
            "min_speech_duration_ms": int(config.settings.get('min_speech_duration_ms',0)),
            "max_speech_duration_s": float(config.settings.get('max_speech_duration_s',5)),
            "min_silence_duration_ms": int(config.settings.get('min_silence_duration_ms',140)),
            "speech_pad_ms": int(config.settings.get('speech_pad_ms',0))
        }
        speech_chunks = get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),
                                              vad_options=VadOptions(**vad_p))
        speech_chunks = convert_to_milliseconds(speech_chunks)

        # 在config.TEMP_DIR下创建一个以当前时间戳为名的文件夹，用于保存切割后的音频片段
        dir_name = f"{config.TEMP_DIR}/{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        data = []
        audio = AudioSegment.from_wav(self.audio_file)
        for i,it in enumerate(speech_chunks):
            start_ms, end_ms = it['start'], it['end']
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({"line":i+1,"text":"","start_time": start_ms, "end_time": end_ms, "file": file_name})

        return data
    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
