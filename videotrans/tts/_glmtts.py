import json
import logging
from typing import Union, List, Dict
import requests
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed, before_log, after_log

from videotrans.configure.excepts import StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import params, settings, logger
from videotrans.tts._base import BaseTTS
from dataclasses import dataclass


@dataclass
class GLMTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed = self.get_speed()
        self.volume=self.get_volume()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        url = "https://open.bigmodel.cn/api/paas/v4/audio/speech"

        payload = {
            "model": "glm-tts",
            "input": data_item['text'],
            "voice": data_item['role'],
            "response_format": "wav",
            "speed":min(2.0,max(0.5,self.speed)),
            "volume":min(10.0,max(0.1,self.volume)),
            "stream": False,
            "watermark_enabled":False
        }

        response = requests.post(url, headers={
            'Authorization': f'Bearer {params.get("zhipu_key","")}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False)
        if response.status_code in [401,403,404,434]:
            raise StopTask(response.text)
        content_type = response.headers.get('Content-Type')
        if 'application/json' in content_type:
            return response.text

        with open(data_item['filename'] + "-tmp.wav", 'wb') as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename'] + "-tmp.wav", data_item['filename'])
