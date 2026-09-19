import logging
import re
import traceback
import urllib
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError
from videotrans.configure.config import tr, logger, settings, TEMP_ROOT
from videotrans.translator._base import BaseTrans
from pathlib import Path


@dataclass
class GoogleTrans(BaseTrans):

    # 实际发出请求获取结果
    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _item_task(self, data: str) -> str:
        if self._exit(): return
        logger.debug(f'[googletrans] {self.target_code=} {self.source_code=}')
        result_list=[]
        import asyncio
        from googletrans import Translator
        async def translate_bulk():
            async with Translator() as translator:
                translations = await translator.translate(data, dest=self.target_code)
                result_list.append(translations.text)
        try:
            asyncio.run(translate_bulk())
            return result_list[0] if result_list else ''
        except BaseException:
            raise TranslateSrtError(f'GoogleTranslate:{traceback.format_exc()[-3:]}')



