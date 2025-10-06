# zh_recogn 识别
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import dashscope
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class Qwen3ASRRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        api_key=config.params.get('qwenmt_key','')
        model=config.params.get('qwenmt_asr_model','qwen3-asr-flash')
        for i, it in enumerate(raws):
            response = dashscope.MultiModalConversation.call(
                # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
                api_key=api_key,
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"audio": it['file']},
                    ]
                }],
                result_format="message",
                asr_options={
                    "language": self.detect_language[:2].lower(), # 可选，若已知音频的语种，可通过该参数指定待识别语种，以提升识别准确率
                    "enable_lid": True,
                    "enable_itn": False
                }
            )
            if not hasattr(response, 'output') or not hasattr(response.output, 'choices'):
                raise StopRetry(f'{response.code}:{response.message}')
            txt=''
            for t in response.output.choices[0]['message']['content']:
                txt += t['text']
            raws[i]['text'] = txt
        return raws

    def cut_audio(self):

        sampling_rate = 16000

        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import (
            VadOptions,
            get_speech_timestamps
        )

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
        audio = AudioSegment.from_file(self.audio_file, format=self.audio_file[-3:])
        for it in speech_chunks:
            start_ms, end_ms = it['start'], it['end']
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({
                "start_time": start_ms,
                "end_time": end_ms,
                "file": file_name,
                "text": "",
                "time": tools.ms_to_time_string(ms=start_ms) + ' --> ' + tools.ms_to_time_string(ms=end_ms)
            })

        return data

