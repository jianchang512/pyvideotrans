import logging
from dataclasses import dataclass
from typing import Union, Dict, List

import requests
from videotrans.configure.config import params, settings, logger,tr
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log


@dataclass
class KokoroTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

        api_url = 'http://' + params.get('kokoro_api','').strip().rstrip('/').lower().replace('http://', '')
        if len(api_url)<10:
            raise StopTask(f'API URL is error: {api_url}')

        if not api_url.endswith('/v1/audio/speech'):
            api_url += '/v1/audio/speech'
        self.api_url=api_url
        self.speed=self.get_speed()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        data = {"input": data_item['text'], "voice": data_item['role'], "speed": self.speed}
        
        try:
            res = requests.post(self.api_url, json=data,  timeout=3600)
        except requests.exceptions.ConnectionError as e:
            if "Failed to establish a new connection" in str(e):
                raise StopTask(f"[Kokoro-TTS] {tr('This channel needs deployed and started before available')}") from e
        res.raise_for_status()
        with open(data_item['filename'] + ".mp3", 'wb') as f:
            f.write(res.content)
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

