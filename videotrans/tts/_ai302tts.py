import json
import logging
from typing import Union, Dict, List
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import settings, params,  logger, ROOT_DIR
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from videotrans.configure import contants
from dataclasses import dataclass


@dataclass
class AI302(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        with open(ROOT_DIR + "/videotrans/voicejson/302.json", 'r', encoding='utf-8') as f:
            ai302_voice_roles = json.loads(f.read())
            self.AI302_doubao = ai302_voice_roles.get("AI302_doubao", {})
            self.AI302_minimaxi = ai302_voice_roles.get("AI302_minimaxi", {})
            self.AI302_dubbingx = ai302_voice_roles.get("AI302_dubbingx", {})
            self.AI302_doubao_ja = ai302_voice_roles.get("AI302_doubao_ja", {})
        self.AI302_openai= contants.OPENAITTS_ROLES.split(",")
        self.speed=self.get_speed()
        self.volume=self.get_volume()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        payload = {
            "provider": "",
            "text": data_item['text'],
            "voice": data_item['role'],
            "output_format": "mp3",
            "speed": self.speed,
            "volume": self.volume
        }
        if data_item['role'] in self.AI302_doubao or data_item['role'] in self.AI302_doubao_ja:
            payload['provider'] = 'doubao'
            payload['voice'] = self.AI302_doubao.get(data_item['role'],self.AI302_doubao_ja.get(data_item['role']))
        elif data_item['role'] in self.AI302_minimaxi:
            payload['provider'] = 'minimaxi'
            payload['model'] = 'speech-02-hd'
            payload['voice'] = self.AI302_minimaxi.get(data_item['role'])
        elif data_item['role'] in self.AI302_dubbingx:
            payload['provider'] = 'dubbingx'
            payload['voice'] = self.AI302_dubbingx.get(data_item['role'])
        elif data_item['role'] in self.AI302_openai:
            payload['provider'] = 'openai'
            payload['model'] = 'gpt-4o-mini-tts'
            payload['voice'] = data_item['role']
        else:
            payload['voice'] = tools.get_azure_rolelist(self.language.split('-')[0],data_item['role'])
            payload['provider'] = 'azure'

        response = requests.post('https://api.302.ai/302/v2/audio/tts', headers={
            'Authorization': f'Bearer {params.get("ai302_key","")}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False)
        if response.status_code in [401,403,402,404]:
            raise StopTask(response.text)
        response.raise_for_status()
        res = response.json()
        audio_url = res.get("audio_url")
        if not audio_url:
            return res.get('error', {}).get("message")
        req_audio = requests.get(audio_url)
        req_audio.raise_for_status()
        with open(data_item['filename'] + ".mp3", 'wb') as f:
            f.write(req_audio.content)
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

