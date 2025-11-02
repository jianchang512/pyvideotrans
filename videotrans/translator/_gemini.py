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
from videotrans.configure.config import tr, logs
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
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.model_name = config.params.get("gemini_model",'')

        self.prompt = tools.get_prompt(ainame='gemini',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)
        self.api_keys = config.params.get('gemini_key', '').strip().split(',')
        self.api_url = 'https://generativelanguage.googleapis.com/v1beta/openai/'

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
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
            model = config.params.get("gemini_model","gemini-2.5-flash")
            message=self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=message),
                    ],
                ),
            ]
            generate_content_config = types.GenerateContentConfig(
                max_output_tokens=int(config.params.get("gemini_maxtoken",65530)),
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

                thinking_config = types.ThinkingConfig(
                    thinking_budget=int(config.params.get('gemini_thinking_budget',24576)),
                ),
                system_instruction=[
                    types.Part.from_text(text=tr("You are a top-notch subtitle translation engine.")),
                ],
            )
            logs(f'[Gemini]请求发送:{message=}')
            result = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                result+=chunk.text
                     
            logs(f'{result=}')
            if not result:
                logs(f'[gemini]请求失败',level='warn')
                raise RuntimeError(f"[Gemini]result is empty")
                
            match = re.search(r'<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)',
                              re.sub(r'<think>(.*?)</think>', '', result, re.S | re.I), re.S | re.I)
            if match:
                return match.group(1)
            raise RuntimeError(f"Gemini result is emtpy")
        except errors.APIError as e:
            logs(f'{e=}',level='warn')
            if e.code in [400,403,404,429,500]:
                raise StopRetry(e.message)
            raise RuntimeError(e.message)

