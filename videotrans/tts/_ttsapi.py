import logging
import sys
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.configure.config import tr
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class TTSAPI(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        api_url = config.params.get('ttsapi_url','').strip().rstrip('/').lower()
        if not api_url.startswith('http'):
            self.api_url = 'http://' + api_url
        else:
            self.api_url = api_url
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self) -> None:
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit() or not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
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


            res = self._apirequests(data_item['text'], role, speed, volume, pitch)
            config.logger.debug(f'返回数据 {res["code"]=}')
            if "code" not in res or "msg" not in res or res['code'] != 0:
                raise RuntimeError(f'TTS-API:{res["msg"]}' )

            if 'data' not in res or not res['data']:
                raise RuntimeError( tr("No valid audio address returned"))
            # 返回的是音频url地址
            tmp_filename = data_item['filename'] + ".mp3"
            if isinstance(res['data'], str) and res['data'].startswith('http'):
                url = res['data']
                res = requests.get(url)
                res.raise_for_status()
                with open(tmp_filename, 'wb') as f:
                    f.write(res.content)
            elif isinstance(res['data'], str) and res['data'].startswith('data:audio'):
                # 返回 base64数据
                self._base64_to_audio(res['data'], tmp_filename)
            elif isinstance(res['data'], dict) and 'audio' in res['data']:
                with open(tmp_filename, 'wb') as f:
                    f.write(bytes.fromhex(res['data']['audio']))
            else:
                raise RuntimeError(tr("No valid audio address or base64 audio data returned") )
            self.convert_to_wav(tmp_filename, data_item['filename'])

        _run()

    def _apirequests(self, text, role, speed=1.0, volume=1.0, pitch=0):
        data = {"text": text.strip(),
                "language": self.language[:2] if self.language else "",
                "extra": config.params.get('ttsapi_extra',''),
                "voice": role,
                "ostype": sys.platform,
                "rate": speed}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        config.logger.debug(f'发送数据 {data=}')
        resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers)
        resraw.raise_for_status()
        return resraw.json()


