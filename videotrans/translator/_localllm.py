# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import httpx
from openai import OpenAI
from openai import LengthFinishReasonError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr, logs
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class LocalLLM(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = config.params.get('localllm_api','')
        self._add_internal_host_noproxy(self.api_url)
        self.model_name = config.params.get("localllm_model",'')

        self.prompt = tools.get_prompt(ainame='localllm',aisendsrt=self.aisendsrt).replace('{lang}',
                                                                                      self.target_language_name)


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        model = OpenAI(api_key=config.params.get('localllm_key',''), base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxy_str))
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {'role': 'system',
             'content': tr("You are a top-notch subtitle translation engine.")},
            {'role': 'user',
             'content': self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')},
        ]
        logs(f"\n[localllm]发送请求数据:{message=}")

        response = model.chat.completions.create(
            model=config.params.get('localllm_model',''),
            max_tokens=int(config.params.get('localllm_max_token')) if config.params.get(
                'localllm_max_token') else 4096,
            temperature=float(config.params.get('localllm_temperature', 0.7)),
            top_p=float(config.params.get('localllm_top_p', 1.0)),
            messages=message
        )

        logs(f'[localllm]响应:{response=}')

        if isinstance(response, str):
            raise RuntimeError(f'{response=}')
        
        if not hasattr(response,'choices'):
            raise RuntimeError(str(response))
        if response.choices[0].finish_reason=='length':
            raise LengthFinishReasonError(completion=response)    
        if not response.choices[0].message.content:
            raise RuntimeError(f"[LocalLLM] {response.choices[0].finish_reason}:{response}")
        result = response.choices[0].message.content.strip()
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>',
                          re.sub(r'<think>(.*?)</think>', '', result, re.S | re.I), re.S | re.I)
        if match:
            return match.group(1)
        return result.strip()

