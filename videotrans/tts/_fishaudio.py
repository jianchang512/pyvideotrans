import json
import logging
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file
from videotrans.util.help_role import get_fishaudio_rolelist


@dataclass(repr=False)
class FishAudioApiTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url='https://api.fish.audio/v1/tts'
        rolelist=get_fishaudio_rolelist()
        self.roledict=rolelist.get(self.language.split('-')[0].lower())
        self.speed=self.get_speed()
        self.volume=self.get_volume()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        role = data_item['role'].strip()
        voice_id = self.roledict.get(role)
        payload = {
            "text": data_item.get('text'),
            "temperature": 0.7,
            "top_p": 0.7,

            "reference_id": voice_id,
            "prosody": {
                "speed": max(0.0,min(self.speed,2.0)),
                "volume": self.volume,
                "normalize_loudness": True
            },
            "chunk_length": 300,
            "normalize": True,
            "format": "wav",
            "sample_rate": 44100,
            "latency": "normal",
            "max_new_tokens": 1024,
            "repetition_penalty": 1.2,
            "min_chunk_length": 50,
            "condition_on_previous_chunks": True,
            "early_stop_threshold": 1,
        }
        headers = {
            "model": params.get('fishaudio_model'),
            "Authorization": f"Bearer {params.get('fishaudio_key','')}",
            "Content-Type": "application/json"
        }

        response = requests.request("POST", self.api_url, headers=headers, json=payload)
        if response.status_code != 200 or response.headers.get('Content-Type')!='audio/wav':
            raise StopTask(response.json()['message'] if "message" in response.text else response.text)

        with open(data_item['filename']+'-44100.wav', 'wb') as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename']+"-44100.wav",data_item['filename'])
