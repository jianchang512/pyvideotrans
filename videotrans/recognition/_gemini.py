# zh_recogn 识别
import socket
import time,os,re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, ClassVar,Union

from google.genai.errors import APIError
from pydub import AudioSegment

from pathlib import Path



from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from videotrans.translator import LANGNAME_DICT

from google import genai
from google.genai import types

@dataclass
class GeminiRecogn(BaseRecogn):
    raws: List[Any] = field(default_factory=list, init=False)
    api_keys: List[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self._set_proxy(type='set')
        if self.target_code:
            self.target_code = LANGNAME_DICT.get(self.target_code, self.target_code)

        self.api_keys = config.params.get('gemini_key', '').strip().split(',')


 
 
    def _exec(self):
        seg_list=self.cut_audio()
        nums=int(config.settings.get('gemini_recogn_chunk',50))
        seg_list=[seg_list[i:i + nums] for i in  range(0, len(seg_list), nums)]
        if len(seg_list)<1:
            raise Exception(f'VAD error')
        srt_str_list=[]


        prompt= config.params['gemini_srtprompt']

        for seg_group in seg_list:
            api_key=self.api_keys.pop(0)
            self.api_keys.append(api_key)

            retry=0
            try:
                client = genai.Client(
                        api_key=api_key
                    )
                parts=[]
                for f in seg_group:
                    parts.append(
                        types.Part.from_bytes(
                            mime_type="audio/wav",
                            data=Path(f['file']).read_bytes()
                        )
                    )
                parts.append(types.Part.from_text(text=prompt))


                config.logger.info(f'发送音频到Gemini:prompt={prompt},{seg_group=}')
                generate_content_config = types.GenerateContentConfig(
                    max_output_tokens=65530,
                    thinking_config = types.ThinkingConfig(
                        thinking_budget=0,
                    ),
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE",  # Block most
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE",  # Block most
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE",  # Block most
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE",  # Block none
                        ),
                    ],
                )
                contents = [
                    types.Content(
                        role="user",
                        parts=parts
                    )
                ]
                res_text=""
                for chunk in client.models.generate_content_stream(
                    model=config.params.get('gemini_model'),
                    contents=contents,
                    config=generate_content_config,

                ):
                    res_text+=chunk.text

                config.logger.info(f'gemini返回结果:{res_text=}')
                m=re.findall(r'<audio_text>(.*?)<\/audio_text>',res_text.strip(),re.I|re.S)
                if len(m)<1:
                    continue
                str_s=[]
                for i,f in enumerate(seg_group):
                    if i < len(m):
                        startraw=tools.ms_to_time_string(ms=f['start_time'])
                        endraw=tools.ms_to_time_string(ms=f['end_time'])
                        text=m[i].strip()
                        if not config.params.get('paraformer_spk',False):
                            text=re.sub(r'\[?spk\-?\d{1,}\]','',text,re.I)
                        srt={
                            "line":len(srt_str_list)+1,
                            "start_time":f['start_time'],
                            "end_time":f['end_time'],
                            "startraw":startraw,
                            "endraw":endraw,
                            "text":text
                        }
                        srt_str_list.append(srt)
                        str_s.append(f'{srt["line"]}\n{startraw} --> {endraw}\n{srt["text"]}')
                self._signal(
                    text=('\n\n'.join(str_s))+"\n\n",
                    type='subtitle'
                )

            except APIError as e:
                config.logger.exception(e, exc_info=True)
                raise RuntimeError(f'{e.code}:{e.message}')
            except Exception as e:
                error = str(e)
                config.logger.error(f'[Gemini]请求失败:{error=}')
                raise

        if len(srt_str_list)<1:
            raise Exception('No result:The return format may not meet the requirements')
        return srt_str_list


    # 根据 时间开始结束点，切割音频片段,并保存为wav到临时目录，记录每个wav的绝对路径到list，然后返回该list
    def cut_audio(self):
        
        sampling_rate=16000
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
        vad_p={
            "threshold":float(config.settings['threshold']),
            "min_speech_duration_ms":int(config.settings['min_speech_duration_ms']),
            "max_speech_duration_s":float(config.settings['max_speech_duration_s']) if float(config.settings['max_speech_duration_s'])>0 else float('inf'),
            "min_silence_duration_ms":int(config.settings['min_silence_duration_ms']),
            "speech_pad_ms":int(config.settings['speech_pad_ms'])
        }
        speech_chunks=get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),vad_options=VadOptions(**vad_p))
        speech_chunks=convert_to_milliseconds(speech_chunks)
        
        # 在config.TEMP_DIR下创建一个以当前时间戳为名的文件夹，用于保存切割后的音频片段
        dir_name = f"{config.TEMP_DIR}/{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"Saving segments to {dir_name}")
        data=[]
        audio = AudioSegment.from_wav(self.audio_file)
        for it in speech_chunks:
            start_ms, end_ms=it['start'],it['end']
            chunk = audio[start_ms:end_ms]
            file_name=f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({"start_time":start_ms,"end_time":end_ms,"file":file_name})

        return data