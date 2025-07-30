# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import httpx,requests
from openai import OpenAI, APIConnectionError, APIError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class LocalLLM(BaseTrans):

    prompt: str = field(init=False)


    def __post_init__(self):
        super().__post_init__()

        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = config.params['localllm_api']
        self.model_name = config.params["localllm_model"]

        self.prompt = tools.get_prompt(ainame='localllm', is_srt=self.is_srt).replace('{lang}', self.target_language_name)

        self._check_proxy()


        
    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            return
        try:
            c=httpx.Client(proxy=None)
            c.get(self.api_url)
        except Exception as e:
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies =  pro
                
    def _item_task(self, data: Union[List[str], str]) -> str:
        model = OpenAI(api_key=config.params['localllm_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies))
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {'role': 'system',
             'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
            {'role': 'user',
             'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]
        config.logger.info(f"\n[localllm]发送请求数据:{message=}")
        try:
            response = model.chat.completions.create(
                model=config.params['localllm_model'],
                max_tokens= int(config.params.get('localllm_max_token')) if config.params.get('localllm_max_token') else 4096,
                temperature=float(config.params.get('localllm_temperature',0.7)),
                top_p=float(config.params.get('localllm_top_p',1.0)),
                messages=message
            )
        except APIError as e:
            config.logger.exception(e,exc_info=True)
            raise
        except Exception as e:
            config.logger.exception(e,exc_info=True)
            raise
        config.logger.info(f'[localllm]响应:{response=}')

        if isinstance(response, str):
            raise Exception(f'{response=}')
        
        if hasattr(response,'choices') and response.choices:
            result = response.choices[0].message.content.strip()
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I),re.S|re.I)
            if match:
                return match.group(1)
            return result.strip()

      
        raise Exception(f'[localllm]请求失败:{response=}')

