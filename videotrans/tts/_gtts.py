import logging
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

from gtts import gTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS


@dataclass
class GTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url='https://translate.google.com'
        lans = self.language.split('-')
        if len(lans) > 1:
            self.language = f'{lans[0]}-{lans[1].upper()}'

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        response = gTTS(data_item['text'], lang=self.language, lang_check=False)
        response.save(data_item['filename'] + ".mp3")
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

