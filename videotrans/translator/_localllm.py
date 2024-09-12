# -*- coding: utf-8 -*-
import re
from typing import Union, List

import httpx
from openai import OpenAI

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class LocalLLM(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = config.params['localllm_api']
        if not re.search(r'localhost', self.api_url) and not re.match(r'https?://(\d+\.){3}\d+', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https://": pro, "http://": pro}
        else:
            self.proxies = {"http://": "", "https://": ""}

        self.prompt = config.params['localllm_template'].replace('{lang}', self.target_language)

    def _item_task(self, data: Union[List[str], str]) -> str:
        model = OpenAI(api_key=config.params['localllm_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxies=self.proxies))
        message = [
            {'role': 'system',
             'content': "You are a professional, helpful translation engine that translates only the content in <source> and returns only the translation results" if config.defaulelang != 'zh' else '您是一个有帮助的翻译引擎，只翻译<source>中的内容，并只返回翻译结果'},
            {'role': 'user',
             'content': self.prompt.replace('[TEXT]',
                                            "\n".join([i.strip() for i in data]) if isinstance(data, list) else data)},
        ]
        config.logger.info(f"\n[localllm]发送请求数据:{message=}")
        response = model.chat.completions.create(
            model=config.params['localllm_model'],
            messages=message
        )
        config.logger.info(f'[localllm]响应:{response=}')

        if isinstance(response, str):
            raise Exception(f'{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        elif response.data and response.data['choices']:
            result = response.data['choices'][0]['message']['content'].strip()
        else:
            raise Exception(f'[localllm]请求失败:{response=}')

        result = result.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
        return re.sub(r'\n{2,}', "\n", result)
