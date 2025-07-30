# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class AI302(BaseTrans):
    prompt: str = field(init=False)
    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 500))
        self.proxies = {"http": "", "https": ""}
        self.model_name = config.params['ai302_model']
        self.prompt = tools.get_prompt(ainame='ai302', is_srt=self.is_srt).replace('{lang}', self.target_language_name)

    def _item_task(self, data: Union[List[str], str]) -> str:
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        payload = {
            "model": config.params['ai302_model'],
            "messages": [
                {'role': 'system',
                 'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
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

