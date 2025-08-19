# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from typing import List, Union

import anthropic
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
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
        self.api_url = self._get_url(config.params['claude_api'])
        self.model_name = config.params["claude_model"]

        self.prompt = tools.get_prompt(ainame='claude', is_srt=self.is_srt).replace('{lang}', self.target_language_name)

        self._check_proxy()

    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            return

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

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

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
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
            api_key=config.params['claude_key'],
            http_client=httpx.Client(proxy=self.proxies)
        )

        response = client.messages.create(
            model=config.params['claude_model'],
            max_tokens=8096,
            system="You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。',
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
