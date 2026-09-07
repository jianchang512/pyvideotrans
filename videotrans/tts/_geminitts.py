import logging
import mimetypes
import struct
from dataclasses import dataclass, field
from typing import Union, Dict, List

from google import genai
from google.genai.errors import APIError
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file
import wave
import base64


@dataclass
class GEMINITTS(BaseTTS):
    api_keys: List[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.api_keys = params.get('gemini_key', '').strip().split(',')


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT+(APIError,)), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        role = data_item['role']
        try:
            self.generate_tts_segment(data_item['text'], role, params.get('gemini_ttsmodel',''),
                                      data_item['filename'] + '.wav')
        except APIError as e:
            raise StopTask(e.message)
        self.convert_to_wav(data_item['filename'] + '.wav', data_item['filename'])

    @staticmethod
    def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)


    def generate_tts_segment(self,text, voice, model, file_name):
        api_key = self.api_keys.pop(0)
        self.api_keys.append(api_key)
        client = genai.Client(
            api_key=api_key,
            http_options = types.HttpOptions(
                client_args={'proxy': self.proxy_str},
                async_client_args={'proxy': self.proxy_str},
            ) if self.proxy_str else None
        )


        interaction = client.interactions.create(
            model=model,
            input=text,
            response_format={"type": "audio"},
            generation_config={
                "speech_config": [
                    {"voice": voice}
                ]
            }
        )

        self.wave_file(file_name, base64.b64decode(interaction.output_audio.data))

