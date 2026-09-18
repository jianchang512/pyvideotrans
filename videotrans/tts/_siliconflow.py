import json
import logging
from typing import Union, Dict, List
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import settings, params,  logger, ROOT_DIR
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.configure import constants
from dataclasses import dataclass

from videotrans.util.help_misc import vail_file
from videotrans.util.help_role import get_azure_rolelist


@dataclass
class SiliconflowTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get('guiji_key')
        self.model_name = params.get('guiji_tts_model','FunAudioLLM/CosyVoice2-0.5B')
        self.speed=self.get_speed()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        url = "https://api.siliconflow.cn/v1/audio/speech"
        payload = {
            "model": self.model_name,
            "input": data_item['text'],
            "voice": f"{self.model_name}:{data_item['role']}",
            "speed": self.speed,
            "response_format": "wav"
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        with open(data_item['filename'] + "-44100.wav", 'wb') as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename'] + "-44100.wav", data_item['filename'])

