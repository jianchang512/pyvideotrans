import json
import logging

import requests
from tenacity import RetryError,retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import tr, settings, params, app_cfg, logger, ROOT_DIR
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools, contants

import os
from openai import OpenAI,AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError

import base64


RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass


@dataclass
class MITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.client = OpenAI(
            api_key=params.get("mitts_key",''),
            base_url="https://api.xiaomimimo.com/v1"
        )
        
    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None,idx:int=-1):
        if self.stop_next_all or self._exit() or  not data_item.get('text','').strip():
            return

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
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
               after=after_log(logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            try:
                completion = self.client.chat.completions.create(
                    model="mimo-v2-tts",
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
            except (AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError):
                self.stop_next_all=True
                raise
        try:
            _run()
        except Exception as e:
            logger.error(f'xiaomi tts配音出错:{e}\n{post_message=}')
            self.error=e
            raise


