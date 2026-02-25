import json
import logging
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log,   RetryError

from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class MinimaxiTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.api_url='https://'+params.get('minimaxi_apiurl','api.minimaxi.com')+'/v1/t2a_v2'
        self.rolelist = {}
        lang_pre = self.language.split('-')[0].lower()
        rolelist=tools.get_minimaxi_rolelist()
        if lang_pre not in rolelist:
            raise StopRetry(f'Dont support language:{self.language}')
        self.rolelist=rolelist[lang_pre]
    def _exec(self) -> None:
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self.stop_next_all or self._exit() or not data_item.get('text','').strip():
            return

        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
                wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
                after=after_log(logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            role = data_item['role'].strip()

            speed = 1.0
            if self.rate:
                speed += float(self.rate.replace('%', '')) / 100
            volume = 1.0
            if self.volume:
                volume += float(self.volume.replace('%', '')) / 100
            pitch = 0
            if self.pitch:
                pitch += int(self.pitch.replace('Hz', ''))
            pitch = min(max(-12, pitch), 12)
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            voice_id = self.rolelist.get(role, 'male-qn-qingse')

            payload = json.dumps({
                "model": params.get('minimaxi_model'),
                "text": data_item.get('text'),
                "stream": False,
                "voice_setting": {
                    "voice_id": voice_id,
                    "speed": speed,
                    "vol": volume,
                    "pitch": pitch,
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
            response.raise_for_status()
            res=response.json()
            logger.debug(f'返回数据 {res["base_resp"]=}')
            if res['base_resp']['status_code'] in [1004,1008,2042,2049,2056]:
                raise StopRetry(res['base_resp']['status_msg'])
            if res['base_resp']['status_code'] != 0:
                raise RuntimeError(res['base_resp']['status_msg'])

            if 'data' not in res or not res['data']:
                raise RuntimeError(f'No valid audio address returned:{res}')

            if isinstance(res['data'], dict) and 'audio' in res['data']:
                with open(data_item['filename']+'.wav', 'wb') as f:
                    f.write(bytes.fromhex(res['data']['audio']))
                self.convert_to_wav(data_item['filename']+".wav",data_item['filename'])
            else:
                raise RuntimeError(f'No valid audio  data returned:{res}')


        _run()