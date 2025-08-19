import logging
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class OTT(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        url = config.params['ott_address'].strip().rstrip('/').lower().replace('/translate', '') + '/translate'
        url = url.replace('//translate', '/translate')
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url = url

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        jsondata = {
            "q": "\n".join(data),
            "source": "auto",
            "target": self.target_code[:2]
        }
        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            raise RuntimeError(f'{result=}')
        return result['translatedText'].strip()
