# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params,settings,logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


@dataclass
class DeepLX(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        url = params.get('deeplx_address','').strip().rstrip('/')
        if len(url)<4:
            raise StopTask(f'API URL is error: {url}')
        key = params.get('deeplx_key','').strip()

        if "/translate" not in url:
            url += '/translate'

        self.api_url = f"http://{url}" if not url.startswith('http') else url
        if key and "key=" not in self.api_url:
            if "?" in self.api_url:
                self.api_url += f"&key={key}"
            else:
                self.api_url += f"?key={key}"


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        target_code = self.target_code.upper()
        if target_code == 'EN':
            target_code = 'EN-US'
        elif target_code == 'ZH-CN':
            target_code = 'ZH-HANS'
        elif target_code == 'ZH-TW':
            target_code = 'ZH-HANT'
        elif target_code == 'PT':
            target_code = 'PT-PT'
        sourcecode = self.source_code.upper()[:2] if self.source_code else None
        sourcecode = sourcecode if sourcecode != 'AUTO' else None
        jsondata = {
            "text": "\n".join(data),
            "source_lang": sourcecode,
            "target_lang": target_code
        }

        response = requests.post(url=self.api_url, json=jsondata)
        response.raise_for_status()
        logger.debug(f'[DeepLX]返回响应,{response=}')

        result = response.json()
        result = tools.cleartext(result['data'])
        return result
