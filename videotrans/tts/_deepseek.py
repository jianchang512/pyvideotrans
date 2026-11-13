import logging
from typing import Union, Dict, List
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import  tr,settings, params, logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from dataclasses import dataclass

from videotrans.util.help_misc import vail_file


@dataclass(repr=False)
class DeepSeekTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        payload={
            "text": data_item['text'],
            "voice_id": data_item['role'],
            "format": "wav",
            "filter_markdown":True
        }
        response = requests.post('https://api.deepseek.com/v1/tools/tts', headers={
            'Authorization': f'Bearer {params.get("deepseek_key","")}',
            'Content-Type': 'application/json'
        }, json=payload, verify=False)
        response.raise_for_status()
        with open(data_item['filename']+'-tmp.wav', "wb") as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename'] + "-tmp.wav", data_item['filename'])





