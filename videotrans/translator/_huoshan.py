# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from openai import OpenAI

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class HuoShan(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self.trans_thread = int(settings.get('aitrans_thread', 50))
        self.model_name = params.get("zijiehuoshan_model",'')

        self.prompt = tools.get_prompt(ainame='zijie',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {'role': 'system',
             'content':'You are a top-tier Subtitle Translation Engine.'},
            {'role': 'user',
             'content': self.prompt.replace('{batch_input}', f'{text}').replace('{context_block}',self.full_origin_subtitles)
             },
        ]
        model_name=params.get('zijiehuoshan_model','')
        pre_=model_name.split('-')[0]
        if pre_ not in['doubao','glm','deepseek','qwen','qwen3','kimi','minimax','minimaxi']:
            model_name='doubao-seed-1-8-251228'
        client = OpenAI(
            base_url='https://ark.cn-beijing.volces.com/api/v3',
            api_key=params.get('zijiehuoshan_key','')
        )

        logger.debug(f"\n[字节火山引擎]发送请求数据:{message=}\n接入点名称:{model_name}")
        response=None
        try:
            response = client.responses.create(
                model=model_name,
                max_output_tokens=32768,
                temperature=float(settings.get('aitrans_temperature',0.2)),
                extra_body={
                    "thinking": {"type": "enabled"},
                },
                input=message
            )
        except Exception as e:            
            raise RuntimeError(e.message) if hasattr(e,'message') else e
        else:
            logger.debug(f'[字节火山引擎]响应:{response=}')
            result = ""
            if not response or response.error:
                raise RuntimeError(response.error)
            if not response.output or len(response.output)<2:
                raise RuntimeError(str(response))
            try:
                result = response.output[-1].content[0].text.strip()
            except Exception as e:
                logger.exception(f'[火山引擎]{e}',exc_info=True)
                raise RuntimeError(str(response.output))

            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>',
                              re.sub(r'<think>(.*?)</think>', '', result, flags=re.I | re.S), flags=re.S | re.I)
            if match:
                return match.group(1)
            return result.strip()
        
