import logging,re
from dataclasses import dataclass
from typing import Union, Dict, List

from openai import OpenAI, AuthenticationError, PermissionDeniedError, NotFoundError,APIConnectionError,APIError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import tr,params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS


@dataclass
class OPENAITTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.api_url = params.get('openaitts_api','')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')
        self.speed=self.get_speed()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        try:
            client = OpenAI(api_key=params.get('openaitts_key', ''), base_url=self.api_url)
            with client.audio.speech.with_streaming_response.create(
                    model=params.get('openaitts_model',''),
                    voice=data_item['role'],
                    input=data_item['text'],
                    speed=self.speed,
                    response_format="wav",
                    instructions=params.get('openaitts_instructions', '')
            ) as response:
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
        except APIConnectionError as e:
            raise StopTask(f'[OpenAITTS] {tr("Unable to connect to API",self.api_url)}\n{e}') from e
        except (NotFoundError,AuthenticationError, PermissionDeniedError) as e:
            raise StopTask(e.message)
        except APIError as e: 
            if re.search(r"insufficient.*?balance",e.message,flags=re.I):
                raise StopTask(tr('The server returned an error message: Insufficient balance',tr('OpenAI-TTS'),self.api_url))
            raise
