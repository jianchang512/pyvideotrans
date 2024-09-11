# -*- coding: utf-8 -*-
import os
import re
import time
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

class DeepLX(BaseTrans):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        url = config.params['deeplx_address'].strip().rstrip('/').replace('/translate', '') + '/translate'
        self.api_url=f"http://{url}" if not url.startswith('http') else url
        if not re.search(r'localhost', url) and not re.match(r'https?://(\d+\.){3}\d+', url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https": pro, "http": pro}
        else:
            self.proxies={"http":"","https":""}
    def _item_task(self,data:Union[List[str],str]) ->str:
        jsondata = {
            "text": "\n".join(data),
            "source_lang":self.source_code.upper()[:2] if self.source_code else None,
            "target_lang":'EN-US' if self.target_language == 'EN' else self.target_language
        }
        config.logger.info(f'[DeepLX]发送请求数据,{jsondata=}')
        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        config.logger.info(f'[DeepLX]返回响应,{response.text=}')
        try:
            result = response.json()
            result = tools.cleartext(result['data'])
        except Exception as e:
            raise Exception(f'无有效返回:{response.text=}')
        return result