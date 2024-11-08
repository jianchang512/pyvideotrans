import random
import re
import time
from typing import Union, List
from urllib.parse import quote

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class Google(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.aisendsrt=False
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    def _item_task_srt(self, data: Union[List[str], str]) -> str:
        text = quote(data)
        print(f'[Google] {text=}')
        url = f"https://translate.google.com/m?sl=auto&tl={self.target_code}&hl={self.target_code}&q={text}"
        config.logger.info(f'[Google] {self.target_code} 请求数据:{url=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
        response = requests.get(url, headers=headers, timeout=300, proxies=self.proxies, verify=False)
        config.logger.info(f'[Google]返回数据:{response.text=}')
        if response.status_code == 429:
            self._signal(text='Google 429 hold on retry')
            time.sleep(random.randint(1, 5))
            return self._item_task_srt(data)
        if response.status_code != 200:
            raise Exception(f'status_code={response.status_code},{response.reason}')

        re_result=re.search(r'<div\s+class=\Wresult-container\W>([^<]+?)<',response.text)
        if not re_result or len(re_result.groups())<1:
            raise Exception(f'no result:{re_result=}')
        return tools.clean_srt(re_result.group(1))


    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.is_srt and self.aisendsrt:
            return self._item_task_srt(data)
        text = "\n".join([quote(text) for text in data]) if isinstance(data, list) else quote(data)
        print(f'[Google] {text=}')
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=auto&tl={self.target_code}&q={text}"
        config.logger.info(f'[Google] {self.target_code} 请求数据:{url=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=300, proxies=self.proxies,verify=False)
        config.logger.info(f'[Google]返回数据:{response.text=}')
        if response.status_code==429:
            self._signal(text='Google 429 hold on retry')
            time.sleep(random.randint(1,5))
            return self._item_task(data)
        if response.status_code != 200:
            raise Exception(f'status_code={response.status_code},{response.reason}')
        re_result = response.json()
        if len(re_result[0]) < 1:
            raise Exception(f'no result:{re_result=}')
        return ("".join([te[0] for te in re_result[0]])).strip()
