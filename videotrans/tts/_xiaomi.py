import logging,re
from typing import Union, Dict, List

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings,tr
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from openai import OpenAI,AuthenticationError, PermissionDeniedError, NotFoundError, APIError
import base64
from dataclasses import dataclass


@dataclass
class XiaoMiTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url="https://api.xiaomimimo.com/v1"

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        refer_text=''
        if idx>-1:
            refer_text=" ".join([it['text'] for it in self.queue_tts[max(0,idx-5):min(idx+6,len(self.queue_tts))]])
        post_message=[
                {
                    "role": "user",
                    "content": refer_text
                },
                {
                    "role": "assistant",
                    "content": data_item.get('text')
                }
        ]

        try:
            self.client = OpenAI(
                api_key=params.get("xiaomi_key",''),
                base_url=self.api_url
            )
            completion = self.client.chat.completions.create(
                model=params.get("xiaomi_ttsmodel"),
                messages=post_message,
                audio={
                    "format": "wav",
                    "voice": data_item['role']
                }
            )

            message = completion.choices[0].message
            audio_bytes = base64.b64decode(message.audio.data)
            with open(data_item['filename']+'-tmp.wav', "wb") as f:
                f.write(audio_bytes)
            self.convert_to_wav(data_item['filename'] + "-tmp.wav", data_item['filename'])

        except (NotFoundError,AuthenticationError, PermissionDeniedError) as e:
            raise StopTask(e.message)
        except APIError as e: 
            if re.search(r"insufficient.*?balance",e.message,flags=re.I):
                raise StopTask(tr('The server returned an error message: Insufficient balance',tr('XiaoMi-TTS'),self.api_url))
            raise