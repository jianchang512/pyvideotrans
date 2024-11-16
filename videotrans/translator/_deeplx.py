# -*- coding: utf-8 -*-
import json
import re
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class DeepLX(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        url = config.params['deeplx_address'].strip().rstrip('/')
        key = config.params['deeplx_key'].strip()
        if "/translate" not in url:
            url+='/translate'
        self.api_url = f"http://{url}" if not url.startswith('http') else url
        if key and "key=" not in self.api_url:
            if "?" in self.api_url:
                self.api_url+=f"&key={key}"
            else:
                self.api_url+=f"?key={key}"
            
        if not re.search(r'localhost', url) and not re.match(r'https?://(\d+\.){3}\d+', url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https": pro, "http": pro}
        else:
            self.proxies = {"http": "", "https": ""}

    def _item_task(self, data: Union[List[str], str]) -> str:
        target_code=self.target_code.upper()
        if target_code=='EN':
            target_code='EN-US'
        elif target_code=='ZH-CN':
            target_code='ZH-HANS'
        elif target_code=='ZH-TW':
            target_code='ZH-HANT'
        sourcecode=self.source_code.upper()[:2] if self.source_code else None
        sourcecode=sourcecode if sourcecode!='AUTO' else None 
        jsondata = {
            "text": "\n".join(data),
            "source_lang": sourcecode,
            "target_lang": target_code
        }
        config.logger.info(f'[DeepLX]发送请求数据,{jsondata=}')
        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        if response.status_code != 200:
            raise Exception(f'DeepLx: status_code={response.status_code} {response.reason} {response.text}')
        config.logger.info(f'[DeepLX]返回响应,{response.text=}')
        try:
            result = response.json()
            result = tools.cleartext(result['data'])
        except json.JSONDecoder:
            raise Exception(f'无有效返回:{response.text=}')
        except Exception as e:
            raise Exception(f'无有效返回 {response.status_code} {response.reason}:{response.text=} ')
        return result
