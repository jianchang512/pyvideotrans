# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class Libre(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        url = params.get('libre_address','').strip().rstrip('/')
        key = params.get('libre_key','').strip()  # Retained for logical equivalence

        if "/translate" not in url:
            url += '/translate'

        self.api_url = f"http://{url}" if not url.startswith('http') else url
        if key and "key=" not in self.api_url:
            if "?" in self.api_url:
                self.api_url += f"&key={key}"
            else:
                self.api_url += f"?key={key}"
        self._add_internal_host_noproxy(self.api_url)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        jsondata = {
            "q": "\n".join(data),
            "source": 'auto',
            "api_key": params.get('libre_key', ''),
            "target": self.target_code[:2]
        }
        logger.info(f'[Libre]发送请求数据,{jsondata=}')

        response = requests.post(url=self.api_url, json=jsondata)
        response.raise_for_status()
        result = response.json()
        result = tools.cleartext(result['translatedText'])

        return result.lower() if self.target_code[:2] == 'en' else result
