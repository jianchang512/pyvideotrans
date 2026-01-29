import json
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass


@dataclass
class AI302(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        with open(config.ROOT_DIR + "/videotrans/voicejson/302.json", 'r', encoding='utf-8') as f:
            ai302_voice_roles = json.loads(f.read())
            self.AI302_doubao = ai302_voice_roles.get("AI302_doubao", {})
            self.AI302_minimaxi = ai302_voice_roles.get("AI302_minimaxi", {})
            self.AI302_dubbingx = ai302_voice_roles.get("AI302_dubbingx", {})
            self.AI302_doubao_ja = ai302_voice_roles.get("AI302_doubao_ja", {})
        self.AI302_openai=config.OPENAITTS_ROLES.split(",")

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self.stop_next_all or self._exit() or  not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            self._generate(data=data_item)

        _run()

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
        if data['role'] in self.AI302_doubao or data['role'] in self.AI302_doubao_ja:
            payload['provider'] = 'doubao'
            payload['voice'] = self.AI302_doubao.get(data['role'],self.AI302_doubao_ja.get(data['role']))
        elif data['role'] in self.AI302_minimaxi:
            payload['provider'] = 'minimaxi'
            payload['model'] = 'speech-02-hd'
            payload['voice'] = self.AI302_minimaxi.get(data['role'])
        elif data['role'] in self.AI302_dubbingx:
            payload['provider'] = 'dubbingx'
            payload['voice'] = self.AI302_dubbingx.get(data['role'])
        elif data['role'] in self.AI302_openai:
            payload['provider'] = 'openai'
            payload['model'] = 'gpt-4o-mini-tts'
            payload['voice'] = data['role']
        else:
            payload['voice'] = tools.get_azure_rolelist(self.language.split('-')[0],data['role'])
            payload['provider'] = 'azure'

        response = requests.post('https://api.302.ai/302/v2/audio/tts', headers={
            'Authorization': f'Bearer {config.params.get("ai302_key","")}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False)
        if response.status_code in [401,403,402,404]:
            self.stop_next_all=True
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
