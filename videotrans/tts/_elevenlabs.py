import json
import logging
from dataclasses import dataclass
from typing import Union, Dict, List

from elevenlabs import ElevenLabs, VoiceSettings, UnauthorizedError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import params, logger, ROOT_DIR, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS


@dataclass
class ElevenLabsC(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.speed = self.get_speed()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = data_item['role']
        with open(ROOT_DIR+'/videotrans/voicejson/elevenlabs.json','r',encoding='utf-8') as f:
            jsondata=json.loads(f.read())
        try:
            client = ElevenLabs(
                api_key=params.get('elevenlabstts_key','')
            )
            response = client.text_to_speech.convert(
                text=data_item['text'],
                voice_id=jsondata[role]['voice_id'],
                model_id=params.get("elevenlabstts_models"),

                output_format="mp3_44100_128",

                apply_text_normalization='auto',
                voice_settings=VoiceSettings(
                    speed=self.speed,
                    stability=0.8,
                    similarity_boost=1,
                    style=0,
                    use_speaker_boost=False
                )
            )
            with open(data_item['filename'] + ".mp3", 'wb') as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

        except UnauthorizedError as e:
            raise StopTask(e.body)