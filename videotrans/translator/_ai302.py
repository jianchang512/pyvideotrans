# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class AI302(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 500))
        self.proxies = {"http": "", "https": ""}
        self.model_name = config.params['ai302_model']
        self.prompt = tools.get_prompt(ainame='ai302', is_srt=self.is_srt).replace('{lang}', self.target_language_name)

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        payload = {
            "model": config.params['ai302_model'],
            "messages": [
                {'role': 'system',
                 'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
                {'role': 'user',
                 'content': self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')},
            ]
        }
        response = requests.post('https://api.302.ai/v1/chat/completions', headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {config.params["ai302_key"]}',
            'User-Agent': 'pyvideotrans',
            'Content-Type': 'application/json'
        }, json=payload, verify=False, proxies=self.proxies)

        response.raise_for_status()
        res = response.json()
        result = ""
        if res['choices']:
            result = res['choices'][0]['message']['content']
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()
