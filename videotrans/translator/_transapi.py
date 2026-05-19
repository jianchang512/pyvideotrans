import logging
from dataclasses import dataclass
from typing import List, Union
from urllib.parse import quote
import requests
from tenacity import retry, retry_if_not_exception_type, wait_fixed, stop_after_attempt, before_log, after_log
from videotrans.configure.excepts import TranslateSrtError, NO_RETRY_EXCEPT, StopTask
from videotrans.configure.config import params, logger, settings
from videotrans.translator._base import BaseTrans



@dataclass
class TransAPI(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        url = params.get('trans_api_url','').strip().rstrip('/').lower()
        if len(url)<4:
            raise StopTask(f'API URL is error: {url}')
        if not url.startswith('http'):
            url = f"http://{url}"
        self.api_url = url + ('&' if '?' in url else '/?')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = quote("\n".join(data))
        requrl = f"{self.api_url}target_language={self.target_code}&source_language={self.source_code[:2] if self.source_code else ''}&text={text}&secret={params.get('trans_secret','')}"

        response = requests.get(url=requrl)
        logger.debug(f'[TransAPI]返回:{response=}')
        response.raise_for_status()
        jsdata = response.json()
        if jsdata['code'] != 0:
            raise TranslateSrtError(f'{jsdata=}')
        return jsdata['text']
