from typing import Union, List
from urllib.parse import quote

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class TransAPI(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        url = config.params['trans_api_url'].strip().rstrip('/').lower()
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url = url + ('&' if url.find('?') > 0 else '/?')
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 实际发出请求获取结果
    def _item_task(self, data: Union[List[str], str]) -> str:
        text = quote("\n".join(data))
        requrl = f"{self.api_url}target_language={self.target_code}&source_language={self.source_code[:2] if self.source_code else ''}&text={text}&secret={config.params['trans_secret']}"
        config.logger.info(f'[TransAPI]请求数据：{requrl=}')
        response = requests.get(url=requrl, proxies=self.proxies)
        config.logger.info(f'[TransAPI]返回:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'status_code={response.status_code} {response.reason} {response.text}')
        jsdata = response.json()
        if jsdata['code'] != 0:
            raise Exception(f'{jsdata=}')
        return jsdata['text']
