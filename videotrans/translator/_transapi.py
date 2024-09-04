import time
from urllib.parse import quote

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class TransAPI(BaseTrans):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        url = config.params['trans_api_url'].strip().rstrip('/').lower()
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url=url+ ('&' if url.find('?') > 0 else '/?')
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}


    # 实际发出请求获取结果
    def _get_content(self,data:list):
        text=quote("\n".join(data))
        requrl = f"{self.api_url}target_language={self.target_language}&source_language={self.source_code}&text={text}&secret={config.params['trans_secret']}"
        config.logger.info(f'[TransAPI]请求数据：{requrl=}')
        response = requests.get(url=requrl, proxies=self.proxies)
        config.logger.info(f'[TransAPI]返回:{response.text=}')
        if response.status_code != 200:
            raise LogExcept(f'code={response.status_code=},{response.text}')
        jsdata = response.json()
        if jsdata['code'] != 0:
            raise LogExcept(jsdata['msg'])
        return jsdata['text']
