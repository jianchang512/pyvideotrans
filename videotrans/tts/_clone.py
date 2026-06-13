import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Dict, List

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.configure.config import tr, params, logger, settings
from videotrans.tts._base import BaseTTS


@dataclass
class CloneVoice(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'http://' +params.get('clone_api', '').strip().rstrip('/').lower().replace('http://', '')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        data = {"text": data_item['text'], "language": self.language}
        role = data_item['role']
        if role=='clone'  and (not data_item.get('ref_wav') or not Path(data_item.get('ref_wav')).exists()):
            return tr("No reference audio exists and cannot use clone function")
        
        
        try:
            if role != 'clone':
                # 不是克隆，使用已有声音
                data['voice'] = role
                res = requests.post(f"{self.api_url}/apitts", data=data,timeout=3600)
            else:
                with open(data_item['ref_wav'], 'rb') as f:
                    files = {"audio": f}
                    res = requests.post(f"{self.api_url}/apitts", data=data, files=files,  timeout=3600)
        except requests.exceptions.ConnectionError as e:
            if "Failed to establish a new connection" in str(e):
                raise StopTask(f"[Clone-Voice] {tr('This channel needs deployed and started before available')}") from e

        res.raise_for_status()
        logger.debug(f'clone-voice:{data=},{res.text=}')
        res = res.json()
        if "code" not in res or res['code'] != 0:
            return str(res)

        if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
            self.convert_to_wav(re.sub(r'\\+', '/', res['filename'],flags=re.I | re.S), data_item['filename'])
            return

        resb = requests.get(res['url'])
        resb.raise_for_status()
        with open(data_item['filename'] + ".wav", 'wb') as f:
            f.write(resb.content)
        time.sleep(1)
        self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

