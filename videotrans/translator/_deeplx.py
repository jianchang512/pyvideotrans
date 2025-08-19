# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class DeepLX(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        url = config.params['deeplx_address'].strip().rstrip('/')
        key = config.params['deeplx_key'].strip()

        if "/translate" not in url:
            url += '/translate'

        self.api_url = f"http://{url}" if not url.startswith('http') else url

        if key and "key=" not in self.api_url:
            if "?" in self.api_url:
                self.api_url += f"&key={key}"
            else:
                self.api_url += f"?key={key}"

        if not re.search(r'localhost', url) and not re.match(r'https?://(\d+\.){3}\d+', url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https": pro, "http": pro}
        else:
            self.proxies = {"http": "", "https": ""}

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        target_code = self.target_code.upper()
        if target_code == 'EN':
            target_code = 'EN-US'
        elif target_code == 'ZH-CN':
            target_code = 'ZH-HANS'
        elif target_code == 'ZH-TW':
            target_code = 'ZH-HANT'
        sourcecode = self.source_code.upper()[:2] if self.source_code else None
        sourcecode = sourcecode if sourcecode != 'AUTO' else None
        jsondata = {
            "text": "\n".join(data),
            "source_lang": sourcecode,
            "target_lang": target_code
        }
        config.logger.info(f'[DeepLX]发送请求数据,{jsondata=}')
        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        response.raise_for_status()
        config.logger.info(f'[DeepLX]返回响应,{response.text=}')

        result = response.json()
        result = tools.cleartext(result['data'])
        return result
