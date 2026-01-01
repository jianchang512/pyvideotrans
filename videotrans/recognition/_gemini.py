# zh_recogn 识别
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from google import genai
from google.genai import types,errors
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class GeminiRecogn(BaseRecogn):
    api_keys: List[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self.api_keys = config.params.get('gemini_key', '').strip().split(',')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _req(self,seg_group,api_key,prompt):
        res_text = ""
        try:
            client = genai.Client(
                api_key=api_key,
                http_options = types.HttpOptions(
                    client_args={'proxy': self.proxy_str},
                    async_client_args={'proxy': self.proxy_str},
                )
            )
            parts = []
            for f in seg_group:
                parts.append(
                    types.Part.from_bytes(
                        mime_type="audio/wav",
                        data=Path(f['file']).read_bytes()
                    )
                )
            parts.append(types.Part.from_text(text=prompt))

            config.logger.debug(f'发送音频到Gemini:prompt={prompt},{seg_group=}')
            generate_content_config = types.GenerateContentConfig(
                max_output_tokens=65536,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1,
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
            
            for chunk in client.models.generate_content_stream(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=generate_content_config,

            ):
                if chunk.text is None:
                    continue
                res_text += chunk.text
            return res_text
        except errors.APIError as e:
            if e.code in [400,403,404,429,500]:
                raise StopRetry(e.message)
            return ''
    def _exec(self):
        seg_list = self.cut_audio()
        if len(seg_list) < 1:
            raise RuntimeError(f'VAD error')
        nums = int(config.settings.get('gemini_recogn_chunk', 50))
        seg_list = [seg_list[i:i + nums] for i in range(0, len(seg_list), nums)]
        srt_str_list = []

        prompt = Path(config.ROOT_DIR+'/videotrans/prompts/recogn/gemini_recogn.txt').read_text(encoding='utf-8')
        # 保存说话人
        speaker_list=[]
        for seg_group in seg_list:
            api_key = self.api_keys.pop(0)
            self.api_keys.append(api_key)
            
            res_text=self._req(seg_group,api_key,prompt)
            config.logger.debug(f'gemini返回结果:{res_text=}')
            m = re.findall(r'<audio_text[^\>]*?>(.*?)<\/audio_text>', res_text.strip(), re.I | re.S)
            if len(m) < 1:
                continue
            str_s = []
            for i, f in enumerate(seg_group):
                if i < len(m):
                    startraw = tools.ms_to_time_string(ms=f['start_time'])
                    endraw = tools.ms_to_time_string(ms=f['end_time'])
                    text = m[i].strip()
                    if not text:
                        continue
                    mt=re.match(r'^\[(spk\d+)\]',text,re.I)

                    if mt:
                        speaker_list.append(mt.group(1))
                        text = re.sub(r'^\[spk\d+\]', '', text,flags=re.I | re.S)
                    srt = {
                        "line": len(srt_str_list) + 1,
                        "start_time": f['start_time'],
                        "end_time": f['end_time'],
                        "startraw": startraw,
                        "endraw": endraw,
                        "text": text  
                    }
                    srt_str_list.append(srt)
                    str_s.append(f'{srt["line"]}\n{startraw} --> {endraw}\n{srt["text"]}')
            self._signal(
                text=('\n\n'.join(str_s)) + "\n\n",
                type='subtitle'
            )

        if len(srt_str_list) < 1:
            raise RuntimeError('No result:The return format may not meet the requirements')
        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        return srt_str_list


