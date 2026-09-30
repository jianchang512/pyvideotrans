import logging
from dataclasses import dataclass, field
from typing import List, Dict
from typing import Union

from gtts import gTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file

RETRY_NUMS = settings.get('retry_nums')
RETRY_DELAY = 5


@dataclass
class GTTS(BaseTTS):
    api_url: str = field(default='https://translate.google.com', init=False)

    def __post_init__(self):
        super().__post_init__()



    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if self._exit() or not data_item.get('text','').strip():
            return
        lans = self.language.split('-')
        if len(lans) > 1:
            self.language = f'{lans[0]}-{lans[1].upper()}'
        response = gTTS(data_item['text'], lang=self.language, lang_check=False)
        response.save(data_item['filename'] + ".mp3")
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])
