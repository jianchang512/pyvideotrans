import logging
from dataclasses import dataclass
from typing import List, Union
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class TransAPI(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        url = config.params['trans_api_url'].strip().rstrip('/').lower()
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url = url + ('&' if '?' in url else '/?')

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = quote("\n".join(data))
        requrl = f"{self.api_url}target_language={self.target_code}&source_language={self.source_code[:2] if self.source_code else ''}&text={text}&secret={config.params['trans_secret']}"
        config.logger.info(f'[TransAPI]请求数据：{requrl=}')
        response = requests.get(url=requrl, proxies=self.proxies)
        config.logger.info(f'[TransAPI]返回:{response.text=}')
        response.raise_for_status()
        jsdata = response.json()
        if jsdata['code'] != 0:
            raise RuntimeError(f'{jsdata=}')
        return jsdata['text']
