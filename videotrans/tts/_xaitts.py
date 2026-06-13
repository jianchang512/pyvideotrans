import logging
from typing import Union, Dict, List
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import  tr,settings, params, logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from dataclasses import dataclass


@dataclass
class XAITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.xai_language='auto'
        if self.language and self.language in ['ar','pt','es']:
            self.xai_language= 'ar-SA' if self.language=='ar' else f'{self.language}-{self.language.upper()}'
        elif self.language:
            self.xai_language=self.language[:2]


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        payload={
            "text": data_item['text'],
            "voice_id": data_item['role'],
            "output_format": {
                "codec": "wav",
                "sample_rate": 48000
              },
            "language": self.xai_language
        }
        try:
            response = requests.post('https://api.x.ai/v1/tts', headers={
            'Authorization': f'Bearer {params.get("xaitts_key","")}',
            'Content-Type': 'application/json'
            }, json=payload, verify=False)
        
            if response.status_code in [401,403,404,405,415,422]:
                raise StopTask(response.text)
        except requests.exceptions.ConnectionError as e:
            raise StopTask(f"[XAITTS] {tr('Unable to connect to remote API','X.AI')}") from e
        response.raise_for_status()
        with open(data_item['filename']+'-tmp.wav', "wb") as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename'] + "-tmp.wav", data_item['filename'])





