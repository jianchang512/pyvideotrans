# -*- coding: utf-8 -*-
import time
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from urllib.parse import quote

class MyMemory(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _item_task(self, data: Union[List[str], str]) -> str:
        if not self.source_code or self.source_code=='auto':
            raise Exception(f'该翻译渠道必须明确指定原始语言')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        text="\n".join(data)
        url = f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair={self.source_code}|{self.target_code}"
        config.logger.info(f'[mymemory]请求数据:{url=}')
        response = requests.get(url, proxies=self.proxies, headers=headers,verify=False,  timeout=300)
        config.logger.info(f'[mymemory]返回:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'[mymemory] status={response.status_code=}')
        re_result = response.json()
        if re_result['responseStatus'] != 200:
            raise Exception(f'no result:{re_result["responseData"]["translatedText"]}')
        return re_result["responseData"]["translatedText"].strip()
