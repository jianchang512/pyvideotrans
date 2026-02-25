import json
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.configure.config import params, logger
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass


@dataclass
class GLMTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()


    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit() or  not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
               after=after_log(logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            self._generate(data=data_item)

        _run()

    def _generate(self, data):
        speed = 1.0
        volume = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        if self.volume:
            volume += float(self.volume.replace('%', '')) / 100
        url = "https://open.bigmodel.cn/api/paas/v4/audio/speech"


        payload = {
            "model": "glm-tts",
            "input": data['text'],
            "voice": data['role'],
            "response_format": "wav",
            "speed":min(2,max(0.5,speed)),
            "volume":min(10,max(0.1,volume)),
            "stream": False,
            "watermark_enabled":False
        }

        response = requests.post(url, headers={
            'Authorization': f'Bearer {params.get("zhipu_key","")}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False)
        content_type = response.headers.get('Content-Type')
        if 'application/json' in content_type:
            raise RuntimeError(response.text)
        
        
        with open(data['filename'] + "-tmp.wav", 'wb') as f:
            f.write(response.content)
        self.convert_to_wav(data['filename'] + "-tmp.wav", data['filename'])
