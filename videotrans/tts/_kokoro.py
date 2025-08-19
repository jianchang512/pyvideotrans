import logging
from dataclasses import dataclass

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class KokoroTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

        api_url = config.params['kokoro_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

        if not self.api_url.endswith('/v1/audio/speech'):
            self.api_url += '/v1/audio/speech'

        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            data = {"input": data_item['text'], "voice": data_item['role'], "speed": speed}
            res = requests.post(self.api_url, json=data, proxies=self.proxies, timeout=3600)
            res.raise_for_status()
            with open(data_item['filename'] + ".mp3", 'wb') as f:
                f.write(res.content)
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
