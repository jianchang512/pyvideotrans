# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

from openai import OpenAI
from openai import LengthFinishReasonError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class SILICONFLOW(BaseTrans):
    prompt: str = field(init=False)
    api_key: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.model_name = config.params.get('guiji_model', '')
        self.api_url = "https://api.siliconflow.cn/v1"

        self.api_key = config.params.get('guiji_key', '')
        self.prompt = tools.get_prompt(ainame='siliconflow',aisendsrt=self.aisendsrt).replace('{lang}',
                                                                                         self.target_language_name)

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {
                'role': 'system',
                'content':'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.debug(f"\n[siliconflow]发送请求数据:{message=}")
        model = OpenAI(api_key=self.api_key, base_url=self.api_url)

        response = model.chat.completions.create(
            model=self.model_name,
            messages=message,
            max_tokens=int(config.params.get('guiji_max_tokens',4096))
        )

        config.logger.debug(f'[siliconflow]响应:{response=}')
        if not hasattr(response,'choices'):
            raise RuntimeError(str(response))
        if response.choices[0].finish_reason=='length':
            raise LengthFinishReasonError(completion=response)
        result = ""
        if response.choices[0].message.content:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.warning(f'[siliconflow]请求失败:{response=}')
            raise RuntimeError(f"[SiliconFlow] {response.choices[0].finish_reason}:{response}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()
