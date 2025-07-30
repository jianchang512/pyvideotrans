# -*- coding: utf-8 -*-
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import httpx,requests
from openai import OpenAI, APIConnectionError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class OpenRouter(BaseTrans):
    prompt: str = field(init=False)
    api_key: str = field(init=False)

    def __post_init__(self):

        super().__post_init__()


        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.model_name = config.params.get('openrouter_model', "")
        self.api_url = 'https://openrouter.ai/api/v1'

        self.prompt = tools.get_prompt(ainame='openrouter', is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.api_key = config.params.get('openrouter_key', '')


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

        config.logger.info(f"\n[openrouter]发送请求数据:{message=}")
        pro = self._set_proxy(type='set')
        
        model = OpenAI(api_key=self.api_key, base_url=self.api_url,http_client=httpx.Client(proxy=pro,timeout=7200))
        try:
            response = model.chat.completions.create(
                model=self.model_name,
                messages=message,
                max_tokens=8092
            )
        except APIConnectionError:
            raise requests.ConnectionError('Network connection failed')
        config.logger.info(f'[openrouter]响应:{response=}')
        result=""
        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[openrouter]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")
        
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
        if match:
            return match.group(1)
        return result.strip()

