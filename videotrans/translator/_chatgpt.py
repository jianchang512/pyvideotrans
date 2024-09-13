# -*- coding: utf-8 -*-
import re
from typing import Union, List

import httpx
from openai import OpenAI

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class ChatGPT(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = self._get_url(config.params['chatgpt_api'])
        if not re.search('localhost', self.api_url) and not re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https://": pro, "http://": pro}
        self.prompt = config.params['chatgpt_template'].replace('{lang}', self.target_language)

    def _get_url(self, url=""):
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if not url or url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"
        # 存在 /v1/xx的，改为 /v1
        if re.match(r'.*/v1/(chat)?(/?completions)?$', url):
            return re.sub(r'/v1.*$', '/v1', url)
        # 不是/v1结尾的改为 /v1
        if url.find('/v1') == -1:
            return url + "/v1"
        return url

    def _item_task(self, data: Union[List[str], str]) -> str:
        message = [
            {
                'role': 'system',
                'content': "You are a professional, helpful translation engine that translates only the content in <source> and returns only the translation results" if config.defaulelang != 'zh' else '您是一个有帮助的翻译引擎，只翻译<source>中的内容，并只返回翻译结果'},
            {
                'role': 'user',
                'content': self.prompt.replace('[TEXT]', "\n".join([i.strip() for i in data]) if isinstance(data,
                                                                                                            list) else data)},
        ]
        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxies=self.proxies))
        response = model.chat.completions.create(
            model='gpt-4o-mini' if config.params['chatgpt_model'].lower().find('gpt-3.5') > -1 else config.params[
                'chatgpt_model'],
            messages=message
        )
        config.logger.info(f'[chatGPT]响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        result = result.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
        return re.sub(r'\n{2,}', "\n", result)
