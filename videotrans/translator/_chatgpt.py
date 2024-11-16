# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import Union, List

import httpx,requests
from openai import OpenAI, APIConnectionError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class ChatGPT(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = self._get_url(config.params['chatgpt_api'])
        if not config.params['chatgpt_key']:
            raise Exception('必须在翻译设置 - OpenAI ChatGPT 填写 SK' if config.defaulelang=='zh' else 'please input your sk password')
        
        # 是srt则获取srt的提示词
        self.prompt = tools.get_prompt(ainame='chatgpt',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()
        self.model_name=config.params["chatgpt_model"]
        self.prompt=self._replace_prompt()
        
    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            return
        try:
            c=httpx.Client(proxies=None)
            c.get(self.api_url)
        except Exception as e:
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https://": pro, "http://": pro}

    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"
        if url.endswith('/v1'):
            return url
        # 存在 /v1/xx的，改为 /v1
        if url.endswith('/v1/chat/completions'):
            return re.sub(r'/v1.*$', '/v1', url)

        if re.match(r'^https?://[^/]+[a-zA-Z]+$',url):
            return url + "/v1"
        return url

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
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
        try:
            response = model.chat.completions.create(
                model='gpt-4o-mini' if config.params['chatgpt_model'].lower().find('gpt-3.5') > -1 else config.params[
                    'chatgpt_model'],
                messages=message
            )
        except APIConnectionError:
            raise requests.ConnectionError('Network connection failed')
        config.logger.info(f'[chatGPT]响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        result = result.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
        return result

    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        message = [
            {
                'role': 'system',
                'content':  "You are an SRT subtitle translation engine that can translate SRT subtitles strictly according to instructions." if config.defaulelang != 'zh' else '您是一个SRT字幕翻译引擎，能严格遵照指令翻译SRT字幕。'},
            {
                'role': 'user',
                'content': prompt},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxies=self.proxies))
        try:
            response = model.chat.completions.create(
                model=config.params['chatgpt_model'],
                messages=message
            )
        except APIConnectionError:
            raise requests.ConnectionError('Network connection failed')
        config.logger.info(f'[chatGPT]响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', result, re.S)
        if match:
            return match.group(1)
        raise Exception(f"Error: {response=}")