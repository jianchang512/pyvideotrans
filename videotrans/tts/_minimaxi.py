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
from videotrans.util import tools



@dataclass
class MinimaxiTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.api_url='https://'+params.get('minimaxi_apiurl','api.minimaxi.com')+'/v1/t2a_v2'
        rolelist=tools.get_minimaxi_rolelist()
        self.rolelist=rolelist.get(self.language.split('-')[0].lower())
        self.speed=self.get_speed()
        self.volume=self.get_volume()
        pitch = self.get_pitch()
        self.pitch = min(max(-12, int(pitch)), 12)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = data_item['role'].strip()
        voice_id = self.rolelist.get(role, 'male-qn-qingse')
        payload = json.dumps({
            "model": params.get('minimaxi_model'),
            "text": data_item.get('text'),
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": self.speed,
                "vol": self.volume,
                "pitch": self.pitch,
                "emotion": params.get('minimaxi_emotion', 'happy'),
                "text_normalization": True,
            },
            "language_boost": 'auto' if self.language!='yue' else 'Chinese,Yue',
            "audio_setting": {
                "sample_rate": 44100,
                "format": "wav",
                "channel": 1
            }
        }, ensure_ascii=False)

        headers = {
            'Authorization': f"Bearer {params.get('minimaxi_apikey','')}",
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", self.api_url, headers=headers, data=payload)
        if response.status_code in [401,403,404,405]:
            raise StopTask(response.text)
        response.raise_for_status()
        res=response.json()
        logger.debug(f'返回数据 {res["base_resp"]=}')
        if res['base_resp']['status_code'] in [1004,1008,2042,2049,2056]:
            raise StopTask(res['base_resp']['status_msg'])
        if res['base_resp']['status_code'] != 0:
            return res['base_resp']['status_msg']

        if 'data' not in res or not res['data']:
            return f'No valid audio address returned:{res}'

        if isinstance(res['data'], dict) and 'audio' in res['data']:
            with open(data_item['filename']+'.wav', 'wb') as f:
                f.write(bytes.fromhex(res['data']['audio']))
            self.convert_to_wav(data_item['filename']+".wav",data_item['filename'])
        else:
            return f'No valid audio  data returned:{res}'
