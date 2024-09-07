from typing import Union, List

import requests

from videotrans.translator._base import BaseTrans
from urllib.parse import quote
from videotrans.configure import config

class Google(BaseTrans):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    def _item_task(self,data:Union[List[str],str]) ->str:
        text="\n".join([quote(text) for text in data])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=auto&tl={self.target_language}&q={text}"
        config.logger.info(f'[Google]请求数据:{url=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=300, proxies=self.proxies)
        config.logger.info(f'[Google]返回数据:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'{response.status_code=},{response.reason=}')

        re_result = response.json()
        if len(re_result[0]) < 1:
            raise Exception( f'no result:{re_result=}')
        return ("".join([te[0] for te in re_result[0]])).strip()

