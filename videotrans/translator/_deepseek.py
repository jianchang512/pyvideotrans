# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Union

from openai import OpenAI
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from openai import LengthFinishReasonError

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class DeepSeek(BaseTrans):
    prompt: str = field(init=False)
    api_key: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.model_name = params.get('deepseek_model', "deepseek-chat")
        self.api_url = 'https://api.deepseek.com/v1/'

        self.prompt = tools.get_prompt(ainame='deepseek',aisendsrt=self.aisendsrt).replace('{lang}',self.target_language_name)
        self.api_key = params.get('deepseek_key', '')

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        
        if isinstance(data, list):
            text = "\n".join([i.strip() for i in data])
        else:
            text=data
        
        message = [
            {
                'role': 'system',
                'content': 'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}').replace('{context_block}',self.full_origin_subtitles)
            },
        ]

        model = OpenAI(api_key=self.api_key, base_url=self.api_url)

        response = model.chat.completions.create(
            model=self.model_name,
            messages=message,
            frequency_penalty=0,
            timeout=300,
            temperature=float(settings.get('aitrans_temperature',0.2)),
            max_tokens=8192 if not self.model_name.startswith('deepseek-reasoner') else 65536
        )

        logger.debug(f'[deepseek]响应:{response=}')
        result = ""
        if not hasattr(response,'choices'):
            raise RuntimeError(str(response))
        if response.choices[0].finish_reason=='length':
            raise LengthFinishReasonError(completion=response)
        if response.choices[0].message.content:
            result = response.choices[0].message.content.strip()
        else:
            logger.warning(f'[deepseek]请求失败:{response=}')
            raise RuntimeError(f"[DeepSeek] {response.choices[0].finish_reason}:{response}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()
