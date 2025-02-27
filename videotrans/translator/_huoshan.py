# -*- coding: utf-8 -*-
import re
from typing import Union, List

import requests
from requests import JSONDecodeError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class HuoShan(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self.proxies = {"http": "", "https": ""}
        self.prompt = tools.get_prompt(ainame='zijie',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.model_name=config.params["zijiehuoshan_model"]

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {'role': 'system',
             'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {'role': 'user',
             'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]
        config.logger.info(f"\n[字节火山引擎]发送请求数据:{message=}\n接入点名称:{config.params['zijiehuoshan_model']}")

        try:
            req = {
                "model": config.params['zijiehuoshan_model'],
                "messages": message
            }
            resp = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                                 proxies=self.proxies, json=req, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.params['zijiehuoshan_key']}"
                })
            if resp.status_code!=200:
                raise Exception(f'字节火山引擎请求失败: status_code={resp.status_code} {resp.reason}')
            config.logger.info(f'[字节火山引擎]响应:{resp.text=}')
            data = resp.json()
            if 'choices' not in data or len(data['choices']) < 1:
                raise Exception(f'字节火山翻译失败:{resp.text=}')
            result = data['choices'][0]['message']['content'].strip()
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
            if match:
                return match.group(1)
            return result.strip()
        except Exception as e:
            raise Exception(f'字节火山翻译失败:{e}')


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        message = [
            {'role': 'system',
             'content':  "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {'role': 'user',
             'content': prompt
             },
        ]

        config.logger.info(f"\n[字节火山引擎]发送请求数据:{message=}\n接入点名称:{config.params['zijiehuoshan_model']}")

        try:
            req = {
                "model": config.params['zijiehuoshan_model'],
                "messages": message
            }
            resp = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                                 proxies=self.proxies, json=req, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.params['zijiehuoshan_key']}"
                })
            if resp.status_code != 200:
                raise Exception(f'字节火山引擎请求失败: status_code={resp.status_code} {resp.reason}')
            config.logger.info(f'[字节火山引擎]响应:{resp.text=}')
            data = resp.json()
            if 'choices' not in data or len(data['choices']) < 1:
                raise Exception(f'字节火山翻译失败:{resp.text=}')
            result = data['choices'][0]['message']['content'].strip()
            match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', result, re.S)
            if not match:
                match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
            if match:
                return match.group(1)
            return result.strip()
        except Exception as e:
            raise Exception(f'字节火山翻译失败:{e}')
