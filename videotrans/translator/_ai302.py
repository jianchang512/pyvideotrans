# -*- coding: utf-8 -*-
import re
from typing import Union, List

import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class AI302(BaseTrans):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',500))
        self.proxies = {"http": "", "https": ""}
        self.prompt = tools.get_prompt(ainame='ai302',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.model_name=config.params['ai302_model']

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        payload = {
            "model": config.params['ai302_model'],
            "messages": [
                {'role': 'system',
                 'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
                {'role': 'user',
                 'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
            ]
        }
        response = requests.post('https://api.302.ai/v1/chat/completions', headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {config.params["ai302_key"]}',
                'User-Agent': 'pyvideotrans',
                'Content-Type': 'application/json'
            }, json=payload, verify=False, proxies=self.proxies)
        config.logger.info(f'[302.ai]响应:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'status_code={response.status_code} {response.reason}')
        res = response.json()
        result=""        
        if res['choices']:
            result = res['choices'][0]['message']['content']
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
        if match:
            return match.group(1)
        return result.strip()


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')
        payload = {
            "model": config.params['ai302_model'],
            "messages": [
                {'role': 'system',
                 'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
                {'role': 'user',
                 'content': prompt},
            ]
        }
        response = requests.post('https://api.302.ai/v1/chat/completions', headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {config.params["ai302_key"]}',
                'User-Agent': 'pyvideotrans',
                'Content-Type': 'application/json'
            }, json=payload, verify=False, proxies=self.proxies)
        config.logger.info(f'[302.ai]响应:{response.text=}')
        if response.status_code != 200:
            raise Exception(f'status_code={response.status_code} {response.reason}')
        res = response.json()
        if res['choices']:
            result = res['choices'][0]['message']['content']
            match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', result,re.S)
            if not match:
                match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
            if match:
                return match.group(1)
            return result.strip()
        raise Exception(f'{res}')