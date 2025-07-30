import time

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


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

        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                data = {"input": data_item['text'], "voice": data_item['role'], "speed": speed}
                res = requests.post(self.api_url, json=data, proxies=self.proxies, timeout=3600)
                res.raise_for_status()
                with open(data_item['filename'], 'wb') as f:
                    f.write(res.content)
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except (requests.ConnectionError, requests.Timeout) as e:
                config.logger.exception(e,exc_info=True)
                self.error = "连接失败，请检查是否启动了api服务" if config.defaulelang == 'zh' else 'Connection failed, please check if the api service is started'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                self.error = str(e)
                config.logger.exception(e, exc_info=True)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
