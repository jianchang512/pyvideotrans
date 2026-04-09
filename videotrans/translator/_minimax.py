# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Union

from openai import OpenAI, LengthFinishReasonError
from videotrans.configure.config import tr, params, settings, app_cfg, logger
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class MiniMax(BaseTrans):
    prompt: str = field(init=False)
    api_key: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.model_name = params.get('minimax_model', 'MiniMax-M2.7')
        self.api_url = params.get('minimax_api', 'api.minimax.io') 
        #  user input  api.minimax.io/v1 or https://api.minimax.io/v1 
        if not self.api_url.startswith('https'):
            self.api_url = 'https://' +self.api_url
        if not self.api_url.endswith('/v1'):
            self.api_url = self.api_url.strip('/')+"/v1"
            
        self.prompt = tools.get_prompt(ainame='minimax', aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)
        self.api_key = params.get('minimax_key', '')

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {
                'role': 'system',
                'content': 'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}').replace('{context_block}',
                                                                                   self.full_origin_subtitles)
            },
        ]


        # MiniMax temperature must be in (0.0, 1.0], clamp accordingly
        temperature = float(settings.get('aitrans_temperature', 0.2))
        if temperature <= 0:
            temperature = 0.01

        model = OpenAI(api_key=self.api_key, base_url=self.api_url)

        response = model.chat.completions.create(
            model=self.model_name,
            messages=message,
            frequency_penalty=0,
            timeout=300,
            temperature=temperature,
            max_tokens=int(params.get('minimax_max_tokens',8192))
        )

        logger.debug(f'[minimax]响应:{response=}')
        result = ""
        if not hasattr(response, 'choices'):
            raise RuntimeError(str(response))
        if response.choices[0].finish_reason == 'length':
            raise LengthFinishReasonError(completion=response)
        if response.choices[0].message.content:
            result = response.choices[0].message.content.strip()
        else:
            logger.warning(f'[minimax]请求失败:{response=}')
            raise# RuntimeError(f"[MiniMax] {response.choices[0].finish_reason}:{response}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()
