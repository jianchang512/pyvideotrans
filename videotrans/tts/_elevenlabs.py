import io
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterator

import httpx
import elevenlabs
from elevenlabs import ElevenLabs, VoiceSettings
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure.config import logs
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ElevenLabsC(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        # 是否终止所有配音，当出现401 403 授权错误 等不论多少次尝试注定失败的错误，提前终止
        self.stop_next_all=False

    def _item_task(self, data_item: dict = None):
        if self._exit() or not data_item.get('text','').strip():
            return
        if self.stop_next_all:
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
        
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            role = data_item['role']

            speed = 1.0
            if self.rate and self.rate != '+0%':
                speed += float(self.rate.replace('%', ''))

            with open(config.ROOT_DIR+'/videotrans/voicejson/elevenlabs.json','r',encoding='utf-8') as f:
                jsondata=json.loads(f.read())

            try:
                client = ElevenLabs(
                    api_key=config.params.get('elevenlabstts_key',''),
                    httpx_client=httpx.Client(proxy=self.proxy_str)
                )
                response = client.text_to_speech.convert(
                    text=data_item['text'],
                    voice_id=jsondata[role]['voice_id'],
                    model_id=config.params.get("elevenlabstts_models"),

                    output_format="mp3_44100_128",

                    apply_text_normalization='auto',
                    voice_settings=VoiceSettings(
                        speed=speed,
                        stability=0,
                        similarity_boost=0,
                        style=0,
                        use_speaker_boost=True
                    )
                )
                with open(data_item['filename'] + ".mp3", 'wb') as f:
                    for chunk in response:
                        if chunk:
                            f.write(chunk)
            except elevenlabs.core.api_error.ApiError as e:
                if e.status_code in [401,403]:
                    self.stop_next_all=True
                    raise StopRetry(e.body.get('detail',{}).get('message'))
                raise    
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

        try:
            _run()
        except RetryError as e:
            self.error= e.last_attempt.exception()
        except Exception as e:
            self.error = e

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        #self.dub_nums = 1
        self._local_mul_thread()

