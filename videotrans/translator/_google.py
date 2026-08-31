import logging
import re
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
class Google(BaseTrans):

    # 实际发出请求获取结果
    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))),
           wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = urllib.parse.quote("\n".join([i.strip() for i in data]) if isinstance(data, list) else data)

        source_code = 'auto' if not self.source_code or self.source_code == 'auto' else self.source_code

        if source_code == 'auto' and Path(f'{TEMP_ROOT}/detect_language_source_{self.uuid}.txt').is_file():
            source_code = \
            Path(f'{TEMP_ROOT}/detect_language_source_{self.uuid}.txt').read_text(encoding="utf-8").strip().split('-')[
                0]
        if source_code == 'zh':
            source_code = 'zh-TW'

        url = f'https://translate.google.com/m?sl={source_code}&tl={self.target_code}&hl={self.target_code}&q={text}'
        logger.debug(f'[Google] {self.target_code=} {self.source_code=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,zh-HK;q=0.6,ja;q=0.5",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-model": "iPhone",
            "sec-ch-ua-platform": "iOS",
            "sec-ch-ua-platform-version": "18.5"
        }

        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        logger.debug(f'[Google]返回code:{response.status_code=}')

        re_result = re.search(r'<div\s+class=\Wresult-container\W>([^<]+?)<', response.text)
        if not re_result or len(re_result.groups()) < 1:
            raise TranslateSrtError(tr("Google Translate error"))
        return re_result.group(1)
