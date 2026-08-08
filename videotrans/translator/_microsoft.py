# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import tr, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopRetry, TranslateSrtError
from videotrans.translator._base import BaseTrans



@dataclass
class Microsoft(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'https://edge.microsoft.com/translate/translatetext'

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        if not self.target_code:
            raise StopRetry(tr("The target language code is not set correctly and cannot be translated"))
        tocode = self.target_code
        if tocode.lower() == 'zh-cn':
            tocode = 'zh-Hans'
        elif tocode.lower() == 'zh-tw':
            tocode = 'zh-Hant'

        texts = data if isinstance(data, list) else [data]
        url = f"{self.api_url}?from=&to={tocode}&isEnterpriseClient=false"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/json',
        }
        response = requests.post(url, json=texts, headers=headers, verify=False, timeout=300)
        logger.debug(f'[Microsoft]返回:{response=}')
        response.raise_for_status()
        re_result = response.json()
        if not re_result:
            raise TranslateSrtError(f'no result:{re_result=}')
        lines = []
        for item in re_result:
            if not item.get('translations'):
                raise TranslateSrtError(f'no result:{re_result=}')
            lines.append(item['translations'][0]['text'].strip())
        return "\n".join(lines)
