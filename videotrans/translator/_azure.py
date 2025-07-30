# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import httpx,requests
from openai import AzureOpenAI, APIConnectionError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class AzureGPT(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.model_name = config.params["azure_model"]
        self.prompt = tools.get_prompt(ainame='azure', is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()

        
    def _check_proxy(self):
        try:
            c=httpx.Client(proxy=None)
            c.get(config.params["azure_api"])
        except Exception as e:
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro

    def _item_task(self, data: Union[List[str], str]) -> str:
        model = AzureOpenAI(
            api_key=config.params["azure_key"],
            api_version=config.params['azure_version'],
            azure_endpoint=config.params["azure_api"],
            http_client=httpx.Client(proxy=self.proxies)
        )
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {'role': 'system',
             'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
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


