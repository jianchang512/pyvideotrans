# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass
from typing import List, Union

import deepl
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.translator._base import BaseTrans



@dataclass
class DeepL(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = None if not params.get('deepl_api') else params.get('deepl_api','').rstrip('/')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: str) -> str:
        if self._exit(): return
        text =data.strip()

        deepltranslator = deepl.Translator(params.get('deepl_authkey',''), server_url=self.api_url)

        target_code = self.target_code.upper()
        if target_code == 'EN':
            target_code = 'EN-US'
        elif target_code == 'ZH-CN':
            target_code = 'ZH-HANS'
        elif target_code == 'ZH-TW':
            target_code = 'ZH-HANT'
        elif target_code == 'PT':
            target_code = 'PT-PT'
        sourcecode = self.source_code.split('-')[0].upper() if self.source_code else None
        sourcecode = sourcecode if sourcecode != 'AUTO' else None
        result = deepltranslator.translate_text(
            text,
            source_lang=sourcecode,
            target_lang=target_code,
            glossary=params.get('deepl_gid')
        )

        logger.debug(f'[DeepL]返回:{result=}')
        return result.text
