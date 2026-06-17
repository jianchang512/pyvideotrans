import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Union, List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings,tr
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS

@dataclass
class ChatTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        # 从配置中读取并处理 API URL
        self.api_url = 'http://' + params.get('chattts_api','').strip().rstrip('/').lower().replace('http://', '').replace('/tts', '')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        data = {"text": data_item['text'], "voice": data_item['role'], 'prompt': '', 'is_split': 1}
        try:
            res = requests.post(f"{self.api_url}/tts", data=data,  timeout=3600)
        except requests.exceptions.ConnectionError as e:
            if "Failed to establish a new connection" in str(e):
                raise StopTask(f"[ChatTTS] {tr('This channel needs deployed and started before available')}") from e
        res = res.json()
        if res is None:
            return 'ChatTTS端出错，请查看其控制台终端'+f"\n{self.api_url=}"

        if "code" not in res or res['code'] != 0:
            if "msg" in res:
                Path(data_item['filename']).unlink(missing_ok=True)
            return f'{res}'+f"\n{self.api_url=}"

        if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
            self.convert_to_wav(re.sub(r'\\+', '/', res['filename'],flags=re.I | re.S), data_item['filename'])
            return

        resb = requests.get(res['url'])
        resb.raise_for_status()

        logger.debug(f'ChatTTS:resb={resb.status_code=}')
        with open(data_item['filename'] + ".wav", 'wb') as f:
            f.write(resb.content)
        time.sleep(1)
        self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

