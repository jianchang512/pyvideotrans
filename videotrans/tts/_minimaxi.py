import json
import sys
import logging
import sys
import time
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class MinimaxiTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url='https://api.minimaxi.com/v1/t2a_v2'
        self.rolelist = {}
        lang_pre = self.language.split('-')[0].lower()
        rolelist=tools.get_minimaxi_rolelist()
        if lang_pre not in rolelist:
            raise RuntimeError(f'Dont support language:{self.language}')
        self.rolelist=rolelist[lang_pre]
    def _exec(self) -> None:
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
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
                "model": config.params.get('minimaxi_model'),
                "text": data_item.get('text'),
                "stream": False,
                "voice_setting": {
                    "voice_id": voice_id,
                    "speed": speed,
                    "vol": volume,
                    "pitch": pitch,
                    "emotion": config.params.get('minimaxi_emotion', 'happy'),
                    "text_normalization": True,
                },
                "language_boost": 'auto',
                "audio_setting": {
                    "sample_rate": 44100,
                    "format": "wav",
                    "channel": 1
                }
            }, ensure_ascii=False)

            headers = {
                'Authorization': f"Bearer {config.params['minimaxi_apikey']}",
                'Content-Type': 'application/json'
            }

            response = requests.request("POST", self.api_url, headers=headers, data=payload)
            response.raise_for_status()
            res=response.json()
            config.logger.info(f'返回数据 {res}')
            if res['base_resp']['status_code'] != 0:
                raise RuntimeError(res['base_resp']['status_msg'])

            if 'data' not in res or not res['data']:
                raise RuntimeError(f'未返回有效音频地址:{res}' if config.defaulelang == 'zh' else f'No valid audio address returned:{res}')

            if isinstance(res['data'], dict) and 'audio' in res['data']:
                with open(data_item['filename'], 'wb') as f:
                    f.write(bytes.fromhex(res['data']['audio']))
            else:
                raise RuntimeError(f'未返回有效音频数据:{res}' if config.defaulelang == 'zh' else f'No valid audio  data returned:{res}')

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error = e
