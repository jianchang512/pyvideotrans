# -*- coding: utf-8 -*-
import json
import re
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class Libre(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        url = config.params['libre_address'].strip().rstrip('/')
        key = config.params['libre_key'].strip()
        if "/translate" not in url:
            url+='/translate'
        self.api_url = f"http://{url}" if not url.startswith('http') else url

            
        if not re.search(r'localhost', url) and not re.match(r'https?://(\d+\.){3}\d+', url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https": pro, "http": pro}
        else:
            self.proxies = {"http": "", "https": ""}

    def _item_task(self, data: Union[List[str], str]) -> str:
        jsondata = {
            "q": "\n".join(data),
            "source": 'auto',
            "api_key":config.params.get('libre_key',''),
            "target": self.target_code[:2]
        }
        config.logger.info(f'[Libre]发送请求数据,{jsondata=}')

        response = requests.post(url=self.api_url, json=jsondata, proxies=self.proxies)
        config.logger.info(f'[libre]返回响应,{response.text=}')
        if response.status_code != 200:
            raise Exception(f'Libre: status_code={response.status_code} {response.reason} {response.text}')
        try:
            result = response.json()
            result = tools.cleartext(result['translatedText'])
        except json.JSONDecoder:
            raise Exception(f'无有效返回:{response.text=}')
        except Exception as e:
            raise Exception(f'无有效返回 {response.status_code} {response.reason}:{response.text=} ')
        return result.lower()  if self.target_code[:2]=='en' else result
