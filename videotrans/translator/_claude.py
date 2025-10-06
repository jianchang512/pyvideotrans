# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import anthropic
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class Claude(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        # 覆盖父类属性
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = self._get_url(config.params.get('claude_api',''))
        self._add_internal_host_noproxy(self.api_url)
        self.model_name = config.params.get("claude_model",'')

        self.prompt = tools.get_prompt(ainame='claude',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)



    def _get_url(self, url=""):
        if not url:
            return "https://api.anthropic.com"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.endswith('/v1'):
            return url[:-3]

        return url

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {
                'role': 'user',
                'content': [
                    {
                        "type": "text",
                        "text": self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')
                    }
                ]
            }
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")

        client = anthropic.Anthropic(
            base_url=self._get_url(),
            api_key=config.params.get('claude_key',''),
            http_client=httpx.Client(proxy=self.proxy_str)
        )

        response = client.messages.create(
            model=config.params.get('claude_model',''),
            max_tokens=int(config.params.get('chatgpt_max_token', 8192)),
            system=tr("You are a top-notch subtitle translation engine."),
            messages=message
        )

        config.logger.info(f'[claude ai]返回响应:{response=}')
        result = ''
        if response.content:
            result = response.content[0].text.strip()
        else:
            config.logger.error(f'[claude]请求失败:{response=}')
            raise RuntimeError(f"no content:{response=}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()
