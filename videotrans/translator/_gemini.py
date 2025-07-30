# -*- coding: utf-8 -*-

import re
import socket
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

import httpx



from openai import OpenAI, APIError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools




# 代理修改  site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc_asyncio.py __init__方法的 options 添加 ("grpc.http_proxy",os.environ.get('http_proxy') or os.environ.get('https_proxy'))
@dataclass
class Gemini(BaseTrans):
    prompt: str = field(init=False)
    api_keys: List[str] = field(init=False, repr=False) # Use repr=False for sensitive data
    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.model_name = config.params["gemini_model"]

        self.prompt = tools.get_prompt(ainame='gemini', is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.api_keys = config.params.get('gemini_key', '').strip().split(',')
        self.api_url='https://generativelanguage.googleapis.com/v1beta/openai/'

        self._set_proxy(type='set')


    def _item_task(self, data: Union[List[str], str]) -> str:

        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {
                'role': 'system',
                'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.info(f"\n[gemini]发送请求数据:{message=}")
        api_key=self.api_keys.pop(0)
        self.api_keys.append(api_key)
        config.logger.info(f'[Gemini]请求发送:{api_key=},{config.params["gemini_model"]=}')
        model = OpenAI(api_key=api_key, base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies,timeout=7200))
        try:
            response = model.chat.completions.create(
                model=config.params["gemini_model"],
                timeout=7200,
                max_tokens= 8092,
                messages=message
            )
        except APIError as e:
            config.logger.exception(e,exc_info=True)
            raise
        except Exception as e:
            config.logger.exception(e,exc_info=True)
            raise
        config.logger.info(f'[gemini]响应:{response=}')

        result=""
        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[gemini]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I),re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()



