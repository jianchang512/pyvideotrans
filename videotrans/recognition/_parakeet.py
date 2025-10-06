# zh_recogn 识别
import logging
from dataclasses import dataclass
from typing import List, Dict, Union

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ParaketRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params.get('parakeet_address','')
        self._add_internal_host_noproxy(self.api_url)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        # 发送请求

        client = OpenAI(api_key='123456', base_url=self.api_url)

        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model='parakeet_srt_words',
                prompt=self.detect_language[:2].lower(),
                response_format="srt"
            )
            if not transcript or not isinstance(transcript, str):
                raise StopRetry(tr('The returned subtitles have no timestamp and cannot be used'))
        tmp = transcript.split("----..----")
        raws = tools.get_subtitle_from_srt(tmp[0], is_file=False)
        return raws
