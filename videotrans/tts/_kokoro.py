import logging
from dataclasses import dataclass

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class KokoroTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

        api_url = config.params.get('kokoro_api','').strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

        if not self.api_url.endswith('/v1/audio/speech'):
            self.api_url += '/v1/audio/speech'
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit() or not data_item.get('text','').strip():
            return
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate

            data = {"input": data_item['text'], "voice": data_item['role'], "speed": speed}
            res = requests.post(self.api_url, json=data,  timeout=3600)
            res.raise_for_status()
            with open(data_item['filename'] + ".mp3", 'wb') as f:
                f.write(res.content)
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

        _run()
