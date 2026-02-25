# -*- coding: utf-8 -*-

import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import httpx
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.configure.config import tr,settings,params,app_cfg,logger
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

from openai import LengthFinishReasonError

from google import genai
from google.genai import types,errors




RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class Gemini(BaseTrans):
    prompt: str = field(init=False)
    api_keys: List[str] = field(init=False, repr=False)  # Use repr=False for sensitive data

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(settings.get('aitrans_thread', 50))
        self.model_name = params.get("gemini_model",'gemini-2.5-flash')

        self.prompt = tools.get_prompt(ainame='gemini',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)
        self.api_keys = params.get('gemini_key', '').strip().split(',')


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data


        api_key = self.api_keys.pop(0)
        self.api_keys.append(api_key)
        try:
            client = genai.Client(
                api_key=api_key,
                http_options = types.HttpOptions(
                    client_args={'proxy': self.proxy_str},
                    async_client_args={'proxy': self.proxy_str},
                )

            )
            model = params.get("gemini_model","gemini-2.5-flash")
            message=self.prompt.replace('{batch_input}', f'{text}').replace('{context_block}',self.full_origin_subtitles)
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=message),
                    ],
                ),
            ]
            think_cfg=types.ThinkingConfig(
                    thinking_budget=int(params.get('gemini_thinking_budget',24576)),
                )
            if model.startswith('gemini-3'):
                think_cfg=types.ThinkingConfig(
                        thinking_level="HIGH",
                )
                
            generate_content_config = types.GenerateContentConfig(
                temperature=float(settings.get('aitrans_temperature',0.2)),
                max_output_tokens=int(params.get("gemini_maxtoken",65530)),
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    )
                  ],

                thinking_config = think_cfg,
                system_instruction=[
                    types.Part.from_text(text='You are a top-tier Subtitle Translation Engine.'),
                ],
            )
            if model.startswith('gemini-1.') or model.startswith('gemini-2.0'):            
                generate_content_config = types.GenerateContentConfig()
            logger.debug(f'[Gemini]请求发送:{message=}')
            result = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                result+=chunk.text if chunk.text else ""
                     
            logger.debug(f'{result=}')
            if not result:
                logger.warning(f'[gemini]请求失败')
                raise RuntimeError(f"[Gemini]result is empty")
                
            match = re.search(r'<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)',
                              re.sub(r'<think>(.*?)</think>', '', result, flags=re.I | re.S), re.S | re.I)
            if match:
                return match.group(1)
            raise RuntimeError(f"Gemini result is emtpy")
        except errors.APIError as e:
            logger.warning(f'{e=}')
            if e.code in [400,403,404,429,500]:
                raise StopRetry(e.message)
            raise RuntimeError(e.message)

