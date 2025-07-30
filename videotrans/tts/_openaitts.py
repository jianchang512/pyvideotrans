import copy
import re
import time

import httpx
from openai import OpenAI, RateLimitError, APIConnectionError

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class OPENAITTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

        self.copydata = copy.deepcopy(self.queue_tts)
        self.api_url = self._get_url(config.params['openaitts_api'])

        if not re.search('localhost', self.api_url) and not re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro



    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        role = data_item['role']

        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                client = OpenAI(api_key=config.params.get('openaitts_key', ''), base_url=self.api_url,
                                http_client=httpx.Client(proxy=self.proxies, timeout=7200))
                with client.audio.speech.with_streaming_response.create(
                        model=config.params['openaitts_model'],
                        voice=role,
                        input=data_item['text'],
                        timeout=7200,
                        speed=speed,
                        instructions=config.params.get('openaitts_instructions', '')
                ) as response:
                    with open(data_item['filename'], 'wb') as f:
                        for chunk in response.iter_bytes():
                            f.write(chunk)

                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except RateLimitError as e:
                config.logger.exception(e, exc_info=True)
                self.error = '超过频率限制' if config.defaulelang == 'zh' else 'Frequency limit exceeded'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(30)
            except APIConnectionError as e:
                config.logger.exception(e, exc_info=True)
                self.error = '无法连接到OpenAI服务，请尝试使用或更换代理' if config.defaulelang == 'zh' else 'Cannot connect to OpenAI service, please try using or changing proxy'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                config.logger.exception(e, exc_info=True)
                error = str(e)
                self.error = error
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)

    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"
        if url.endswith('/v1'):
            return url
        # 存在 /v1/xx的，改为 /v1
        if re.match(r'.*/v1/.*$', url):
            return re.sub(r'/v1.*$', '/v1', url)

        if re.match(r'^https?://[^/]+[a-zA-Z]+$', url):
            return url + "/v1"
        return url
