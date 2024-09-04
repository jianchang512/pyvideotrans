# -*- coding: utf-8 -*-
import os
import time

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class Microsoft(BaseTrans):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.auth=""
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _get_content(self,data) ->str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        try:
            if not self.auth:
                self.auth = requests.get('https://edge.microsoft.com/translate/auth', headers=headers, proxies=self.proxies)
        except:
            raise LogExcept('连接微软翻译失败，请更换其他翻译渠道' if config.defaulelang == 'zh' else 'Failed to connect to Microsoft Translate, please change to another translation channel')


        url = f"https://api-edge.cognitive.microsofttranslator.com/translate?from=&to={self.target_language}&api-version=3.0&includeSentenceLength=true"
        headers['Authorization'] = f"Bearer {self.auth.text}"
        config.logger.info(f'[Mircosoft]请求数据:{url=},{self.auth.text=}')
        response = requests.post(url, json=[{"Text": "\n".join(data)}], proxies=proxies, headers=headers, timeout=300)
        config.logger.info(f'[Mircosoft]返回:{response.text=}')
        if response.status_code != 200:
            raise LogExcept(f'[Mircosoft] status={response.status_code=}')
        re_result = response.json()
        if len(re_result) == 0 or len(re_result[0]['translations']) == 0:
            raise LogExcept(f'[Mircosoft]:{re_result}')
        return re_result[0]['translations'][0]['text'].strip()

