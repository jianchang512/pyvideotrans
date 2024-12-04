# -*- coding: utf-8 -*-
import time
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class Microsoft(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        self.auth = ""
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _item_task(self, data: Union[List[str], str]) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        auth_num = 3
        while 1:
            auth_num -= 1
            try:
                if not self.auth:
                    self.auth = requests.get('https://edge.microsoft.com/translate/auth', headers=headers,
                                             proxies=self.proxies,verify=False)
                    if self.auth.status_code!=200:
                        raise Exception(f'[Mircosoft]:status_code={self.auth.status_code} {self.auth.reason}')
            except (requests.ConnectionError,requests.HTTPError,requests.Timeout,requests.exceptions.ProxyError):
                raise
            except Exception as e:
                if auth_num <= 0:
                    raise Exception(
                        f'连接微软翻译失败，请更换其他翻译渠道 {e}' if config.defaulelang == 'zh' else f'Failed to connect to Microsoft Translate, please change to another translation channel:{e}')
                time.sleep(5)
            else:
                break
        tocode=self.target_code
        if tocode.lower()=='zh-cn':
            tocode='zh-Hans'
        elif tocode.lower()=='zh-tw':
            tocode='zh-Hant'
        url = f"https://api-edge.cognitive.microsofttranslator.com/translate?from=&to={tocode}&api-version=3.0&includeSentenceLength=true"
        headers['Authorization'] = f"Bearer {self.auth.text}"
        config.logger.info(f'[Mircosoft]请求数据:{url=},{self.auth.text=}')
        response = requests.post(url, json=[{"Text": "\n".join(data)}], proxies=self.proxies, headers=headers,verify=False,  timeout=300)
        config.logger.info(f'[Mircosoft]返回:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'[Mircosoft] status={response.status_code=}')
        re_result = response.json()
        if len(re_result) == 0 or len(re_result[0]['translations']) == 0:
            raise Exception(f'no result:{re_result=}')
        return re_result[0]['translations'][0]['text'].strip()
