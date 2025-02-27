# -*- coding: utf-8 -*-
import re
from typing import Union, List

import httpx,requests
from openai import AzureOpenAI, APIConnectionError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class AzureGPT(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self.prompt = tools.get_prompt(ainame='azure',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()
        self.model_name=config.params["azure_model"]

        
    def _check_proxy(self):
        try:
            c=httpx.Client(proxy=None)
            c.get(config.params["azure_api"])
        except Exception as e:
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        model = AzureOpenAI(
            api_key=config.params["azure_key"],
            api_version=config.params['azure_version'],
            azure_endpoint=config.params["azure_api"],
            http_client=httpx.Client(proxy=self.proxies)
        )
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {'role': 'system',
             'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {'role': 'user',
             'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.info(f"\n[AzureGPT]请求数据:{message=}")
        try:
            response = model.chat.completions.create(
                model=config.params["azure_model"],
                messages=message
            )
        except APIConnectionError:
            raise requests.ConnectionError('Network connection failed')
        config.logger.info(f'[AzureGPT]返回响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[AzureGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
        if match:
            return match.group(1)
        return result.strip()


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        model = AzureOpenAI(
            api_key=config.params["azure_key"],
            api_version=config.params['azure_version'],
            azure_endpoint=config.params["azure_api"],
            http_client=httpx.Client(proxy=self.proxies)
        )
        message = [
            {'role': 'system',
             'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {'role': 'user',
             'content': prompt},
        ]

        config.logger.info(f"\n[AzureGPT]请求数据:{message=}")
        try:
            response = model.chat.completions.create(
                model=config.params["azure_model"],
                messages=message
            )
        except APIConnectionError:
            raise requests.ConnectionError('Network connection failed')
        config.logger.info(f'[AzureGPT]返回响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[AzureGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")
        match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', result,re.S)
        if not match:
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()
    