import json
import logging

import requests
from tenacity import RetryError,retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import tr, settings, params, app_cfg, logger, ROOT_DIR
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools, contants

RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass


@dataclass
class XAITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.xai_language='auto'
        if self.language and self.language in ['ar','pt','es']:
            self.xai_language= 'ar-SA' if self.language=='ar' else f'{self.language}-{self.language.upper()}'
        elif self.language:
            self.xai_language=self.language[:2]
        
    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None,idx:int=-1):
        if self.stop_next_all or self._exit() or  not data_item.get('text','').strip():
            return
        payload={
            "text": data_item['text'],
            "voice_id": data_item['role'],
            "output_format": {
                "codec": "wav",
                "sample_rate": 48000
              },
            "language": self.xai_language
        }
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
               after=after_log(logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            response = requests.post('https://api.x.ai/v1/tts', headers={
                'Authorization': f'Bearer {params.get("xaitts_key","")}',
                'Content-Type': 'application/json'
            }, json=payload, verify=False)
            if response.status_code==400:
                self.stop_next_all=True   
                raise RuntimeError(f'SK is incorrect')
                
            if response.status_code != 200:
                if response.status_code not in [429]:
                    self.stop_next_all=True
                else:
                    self._signal(text=f'retry 429 Error: Too Many Requests  ...')
                response.raise_for_status()
            with open(data_item['filename']+'-tmp.wav', "wb") as f:
                f.write(response.content)
            self.convert_to_wav(data_item['filename'] + "-tmp.wav", data_item['filename'])
        try:
            _run()
        except RetryError as e:
            self.error=str(e.last_attempt.exception())+f"\n{payload=}"
            raise  RuntimeError(self.error)
        except Exception as e:
            self.error=str(e)+f"\n{payload=}"
            raise RuntimeError(self.error)


