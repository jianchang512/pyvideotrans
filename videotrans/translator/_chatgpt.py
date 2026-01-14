# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import httpx
import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from openai import LengthFinishReasonError

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatGPT(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = self._get_url(config.params.get('chatgpt_api',''))
        self._add_internal_host_noproxy(self.api_url)
        self.model_name = config.params.get("chatgpt_model",'')

        self.prompt = tools.get_prompt(ainame='chatgpt',aisendsrt=self.aisendsrt).replace('{lang}',  self.target_language_name)


    def llm_segment(self, srt_list, ai_type='openai'):

        prompts_template = Path(config.ROOT_DIR + '/videotrans/prompts/recharge/recharge-llm.txt').read_text(encoding='utf-8')
        max_speech_s=str(config.settings.get('max_speech_duration_s',6))
        prompts_template=prompts_template.replace('{max_speech_s}',max_speech_s)

        chunk_size = int(config.settings.get('llm_chunk_size', 20))
        api_key = config.params.get('chatgpt_key','') if ai_type == 'openai' else config.params.get('deepseek_key','')
        model_name = config.params.get('chatgpt_model','') if ai_type == 'openai' else config.params.get('deepseek_model','')
        api_url = self._get_url( config.params.get('chatgpt_api','')) if ai_type == 'openai' else 'https://api.deepseek.com/v1'

        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _send(srt):
            message = [
                {"role": "system", "content": prompts_template},
                {
                    'role': 'user',
                    'content': f"""```srt\n{srt}\n```"""
                }
            ]
            config.logger.debug(f'需要断句的:{message=}')
            model = OpenAI(api_key=api_key, base_url=api_url, http_client=httpx.Client(proxy=self.proxy_str))

            response = model.chat.completions.create(
                model=model_name,
                frequency_penalty=0,
                max_completion_tokens=max(int(config.params.get('chatgpt_max_token', 8192)), 8192),
                messages=message,
                temperature=float(config.settings.get('aitrans_temperature',0.2)),
                timeout=300 # 超过5分钟为失败
            )
            if not hasattr(response, 'choices') or not response.choices:
                config.logger.warning(f'[LLM re-segments]重新断句失败:{response=}')
                raise RuntimeError(f"{response}")

            if response.choices[0].finish_reason == 'length':
                raise RuntimeError(f"Please increase max_token")
            if not response.choices[0].message.content:
                config.logger.warning(f'[LLM re-segments]重新断句失败:{response=}')
                raise RuntimeError(f"{response}")

            result = response.choices[0].message.content
            match = re.search(r'<SRT>(.*?)</SRT>', re.sub(r'<think>(.*?)</think>', '', result, flags=re.I | re.S), re.S | re.I)
            config.logger.warning(f'[LLM re-segments]重新断句结果:{result=}')
            if match:
                return match.group(1)
            return result.strip()


        new_sublist = []
        for idx in range(0, len(srt_list), chunk_size):
            self._signal(text=f'[{idx}] {ai_type} '+tr("Re-segmenting..."))
            srt_str = "\n\n".join([f"{line+1}\n{it['time']}\n{it['text']}" for line,it in enumerate(srt_list[idx: idx + chunk_size])])
            new_sublist.append(_send(srt_str))

        return tools.get_subtitle_from_srt("\n\n".join(new_sublist),is_file=False)


    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"

        if url.endswith('/v1'):
            return url
        # 存在 /v1/xx的，改为 /v1
        if url.find('/v1/chat/')>-1:
            return re.sub(r'/v1.*$', '/v1', url,flags=re.I | re.S)

        if re.match(r'^https?://[a-zA-Z0-9_\.-]+$', url):
            return url + "/v1"

        return url

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {
                'role': 'system',
                'content': 'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}').replace('{context_block}',self.full_origin_subtitles)
            },
        ]

        config.logger.debug(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params.get('chatgpt_key',''), base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxy_str, timeout=7200))
        response = model.chat.completions.create(
            model=config.params.get('chatgpt_model',''),
            timeout=300,
            frequency_penalty=0,
            temperature=float(config.settings.get('aitrans_temperature',0.2)),
            max_completion_tokens=int(config.params.get('chatgpt_max_token', 8192)),
            messages=message
        )
        config.logger.debug(f'[chatGPT]响应:{response=}')
        result = ""
        if not hasattr(response,'choices'):
            raise RuntimeError(str(response))
        
        if response.choices[0].finish_reason=='length':
            raise LengthFinishReasonError(completion=response)
        if response.choices[0].message.content:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.warning(f'[chatGPT]请求失败:{response=}')
            raise RuntimeError(f"[OpenAIChatGPT]{response.choices[0].finish_reason}:{response}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>',
                          re.sub(r'<think>(.*?)</think>', '', result, flags=re.I | re.S), re.S | re.I)
        if match:
            return match.group(1)
        return result.strip()
