# -*- coding: utf-8 -*-
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
class Microsoft(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        auth = requests.get('https://edge.microsoft.com/translate/auth', headers=headers,
                            proxies=self.proxies, verify=False)
        auth.raise_for_status()

        tocode = self.target_code
        if tocode.lower() == 'zh-cn':
            tocode = 'zh-Hans'
        elif tocode.lower() == 'zh-tw':
            tocode = 'zh-Hant'
        url = f"https://api-edge.cognitive.microsofttranslator.com/translate?from=&to={tocode}&api-version=3.0&includeSentenceLength=true"
        headers['Authorization'] = f"Bearer {auth.text}"
        config.logger.info(f'[Mircosoft]请求数据:{url=},{auth.text=}')
        response = requests.post(url, json=[{"Text": "\n".join(data)}], proxies=self.proxies, headers=headers,
                                 verify=False, timeout=300)
        config.logger.info(f'[Mircosoft]返回:{response.text=}')
        response.raise_for_status()
        re_result = response.json()
        if len(re_result) == 0 or len(re_result[0]['translations']) == 0:
            raise RuntimeError(f'no result:{re_result=}')
        return re_result[0]['translations'][0]['text'].strip()
