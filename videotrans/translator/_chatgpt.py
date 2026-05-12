# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import httpx
from openai import OpenAI, LengthFinishReasonError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr, app_cfg, settings, params, logger, ROOT_DIR
from videotrans.translator._base import BaseTrans
from videotrans.util import tools
from videotrans.translator._openaicompat import OpenAICampat

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatGPT(OpenAICampat):
    def __post_init__(self):
        self.ainame = "chatgpt"
        self.api_key = params.get('chatgpt_key', '')
        self.api_url = self._get_url(params.get('chatgpt_api', ''))
        self.model_name = params.get("chatgpt_model", '')
        super().__post_init__()
        self._add_internal_host_noproxy(self.api_url)


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
        if url.find('/v1/chat/') > -1:
            return re.sub(r'/v1.*$', '/v1', url, flags=re.I | re.S)

        if re.match(r'^https?://[a-zA-Z0-9_\.-]+$', url):
            return url + "/v1"

        return url
