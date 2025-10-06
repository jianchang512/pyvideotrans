# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass
from typing import List, Union

import deepl
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.translator._base import BaseTrans

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class DeepL(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = None if not config.params.get('deepl_api') else config.params.get('deepl_api','').rstrip('/')
        self._add_internal_host_noproxy(self.api_url)
        self.aisendsrt = False


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = ("\n".join(data)).strip()
        # text可能是中文 英文 日文 越南语等任何一种语言，也可能text全部由特殊符号组成，键盘上可以打出来的所有特殊符号，如果全是符号，则返回原text
        if not text or re.match(r'^[\s ~`!@#$%^&*()_+\-=\[\]{}\\|;,./?><:"\'，。、；‘’“”：《》？【】｛｝（）—！·￥…ー]+$', text):
            return text

        deepltranslator = deepl.Translator(config.params.get('deepl_authkey',''), server_url=self.api_url)
        config.logger.info(f'[DeepL]请求数据:{text=}')
        target_code = self.target_code.upper()
        if target_code == 'EN':
            target_code = 'EN-US'
        elif target_code == 'ZH-CN':
            target_code = 'ZH-HANS'
        elif target_code == 'ZH-TW':
            target_code = 'ZH-HANT'
        elif target_code == 'PT':
            target_code = 'PT-PT'
        sourcecode = self.source_code.upper()[:2] if self.source_code else None
        sourcecode = sourcecode if sourcecode != 'AUTO' else None
        result = deepltranslator.translate_text(
            text,
            source_lang=sourcecode,
            target_lang=target_code,
            glossary=config.params.get('deepl_gid')
        )

        config.logger.info(f'[DeepL]返回:{result=}')
        return result.text
