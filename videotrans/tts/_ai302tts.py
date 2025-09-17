import json
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans import tts
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass


@dataclass
class AI302(BaseTTS):
    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            self._generate(data=data_item)
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error=e

    def _generate(self, data):
        speed = 1.0
        volume = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        if self.volume:
            volume += float(self.volume.replace('%', '')) / 100
        payload = {
            "provider": "",
            "text": data['text'],
            "voice": data['role'],
            "output_format": "mp3",
            "speed": speed,
            "volume": volume
        }
        if data['role'] in tts.AI302_doubao or data['role'] in tts.AI302_doubao_ja:
            payload['provider'] = 'doubao'
            payload['voice'] = tts.AI302_doubao.get(data['role'],tts.AI302_doubao_ja.get(data['role']))
        elif data['role'] in tts.AI302_minimaxi:
            payload['provider'] = 'minimaxi'
            payload['model'] = 'speech-02-hd'
            payload['voice'] = tts.AI302_minimaxi.get(data['role'])
        elif data['role'] in tts.AI302_dubbingx:
            payload['provider'] = 'dubbingx'
            payload['voice'] = tts.AI302_dubbingx.get(data['role'])
        elif data['role'] in tts.AI302_openai:
            payload['provider'] = 'openai'
            payload['model'] = 'gpt-4o-mini-tts'
            payload['voice'] = tts.AI302_openai.get(data['role'])
        else:
            payload['provider'] = 'azure'
        # print(f'{payload=}')
        response = requests.post('https://api.302.ai/302/v2/audio/tts', headers={
            'Authorization': f'Bearer {config.params["ai302_key"]}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False, proxies=None)
        response.raise_for_status()
        res = response.json()
        audio_url = res.get("audio_url")
        if not audio_url:
            raise RuntimeError(res.get('error', {}).get("message"))
        req_audio = requests.get(audio_url)
        req_audio.raise_for_status()
        with open(data['filename'] + ".mp3", 'wb') as f:
            f.write(req_audio.content)
        self.convert_to_wav(data['filename'] + ".mp3", data['filename'])
