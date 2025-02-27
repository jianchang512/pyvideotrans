# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import Union, List

import httpx,requests
from openai import OpenAI, APIConnectionError, APIError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class ChatGPT(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self.api_url = self._get_url(config.params['chatgpt_api'])
        if not config.params['chatgpt_key']:
            raise Exception('必须在翻译设置 - OpenAI ChatGPT 填写 SK' if config.defaulelang=='zh' else 'please input your sk password')
        
        # 是srt则获取srt的提示词
        self.prompt = tools.get_prompt(ainame='chatgpt',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()
        self.model_name=config.params["chatgpt_model"]

        
    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            self.proxies=None
            return
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

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
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data    
        message = [
            {
                'role': 'system',
                'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies,timeout=7200))
        try:
            response = model.chat.completions.create(
                model='gpt-4o-mini' if config.params['chatgpt_model'].lower().find('gpt-3.5') > -1 else config.params['chatgpt_model'],
                timeout=7200,
                max_tokens= int(config.params.get('chatgpt_max_token')) if config.params.get('chatgpt_max_token') else 4096,
                temperature=float(config.params.get('chatgpt_temperature',0.7)),
                top_p=float(config.params.get('chatgpt_top_p',1.0)),
                messages=message
            )
        except APIError as e:
            config.logger.exception(e,exc_info=True)
            raise
        except Exception as e:
            config.logger.exception(e,exc_info=True)
            raise
        config.logger.info(f'[chatGPT]响应:{response=}')
        result=""
        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")
        
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I),re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        message = [
            {
                'role': 'system',
                'content':  "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {
                'role': 'user',
                'content': prompt},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies,timeout=7200))
        try:
            response = model.chat.completions.create(
                model=config.params['chatgpt_model'],
                timeout=7200,
                max_tokens=4096,
                messages=message
            )
        except APIConnectionError as e:
            config.logger.error(f'[chatGPT]:{e=}')
            raise
        config.logger.info(f'[chatGPT]响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if not match:
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()
        