import logging
from dataclasses import dataclass, field
from typing import List, Dict
from typing import Union

from gtts import gTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class GTTS(BaseTTS):
    api_url: str = field(default='https://translate.google.com', init=False)

    def __post_init__(self):
        super().__post_init__()

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            lans = self.language.split('-')
            if len(lans) > 1:
                self.language = f'{lans[0]}-{lans[1].upper()}'
            response = gTTS(data_item['text'], lang=self.language, lang_check=False)
            response.save(data_item['filename'] + ".mp3")
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
