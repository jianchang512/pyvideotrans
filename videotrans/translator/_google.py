import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from urllib.parse import quote

import requests

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from tenacity import retry,stop_after_attempt, stop_after_delay, wait_fixed, retry_if_exception_type, retry_if_not_exception_type, before_log, after_log

RETRY_NUMS=3
RETRY_DELAY=5

@dataclass
class Google(BaseTrans):

    def __post_init__(self):
        super().__post_init__()

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT),stop=(stop_after_attempt(RETRY_NUMS)), wait=wait_fixed(RETRY_DELAY),before=before_log(config.logger,logging.INFO),after=after_log(config.logger,logging.INFO),retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = quote(data)
        url = f"https://translate.google.com/m?sl=auto&tl={self.target_code}&hl={self.target_code}&q={text}"
        config.logger.info(f'[Google] {self.target_code} 请求数据:{url=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
        response = requests.get(url, headers=headers, timeout=300, proxies=self.proxies, verify=False)
        response.raise_for_status()
        config.logger.info(f'[Google]返回数据:{response.status_code=}')

        re_result=re.search(r'<div\s+class=\Wresult-container\W>([^<]+?)<',response.text)
        if not re_result or len(re_result.groups())<1:
            raise Exception(f'no result:{re_result=}')
        return tools.clean_srt(re_result.group(1)) if self.is_srt and self.aisendsrt else re_result.group(1)


