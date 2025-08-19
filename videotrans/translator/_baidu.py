# -*- coding: utf-8 -*-
import hashlib
import logging
import os
import time
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
class Baidu(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        proxy = os.environ.get('http_proxy')
        if proxy:
            if 'http_proxy' in os.environ: del os.environ['http_proxy']
            if 'https_proxy' in os.environ: del os.environ['https_proxy']
            if 'all_proxy' in os.environ: del os.environ['all_proxy']

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join(data)
        salt = int(time.time())
        strtext = f"{config.params['baidu_appid']}{text}{salt}{config.params['baidu_miyue']}"
        md5 = hashlib.md5()
        md5.update(strtext.encode('utf-8'))
        sign = md5.hexdigest()
        tocode = self.target_code
        if tocode.lower() == 'zh-tw':
            tocode = 'cht'
        elif tocode.lower() == 'zh-cn':
            tocode = 'zh'
        requrl = f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={tocode}&appid={config.params['baidu_appid']}&salt={salt}&sign={sign}"

        config.logger.info(f'[Baidu]请求数据:{requrl=}')
        resraw = requests.get(requrl, proxies={"http": "", "https": ""})
        resraw.raise_for_status()
        res = resraw.json()
        config.logger.info(f'[Baidu]返回响应:{res=}')

        if "error_code" in res or "trans_result" not in res or len(res['trans_result']) < 1:
            config.logger.info(f'Baidu 返回响应:{resraw}')
            raise RuntimeError(res['error_msg'])

        result = [tools.cleartext(tres['dst']) for tres in res['trans_result']]
        if not result or len(result) < 1:
            raise RuntimeError(f'no result:{res=}')
        return "\n".join(result)
