# zh_recogn 识别
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ParaketRecogn(BaseRecogn):
    raws: List[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params['parakeet_address']
        self.proxies = None

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
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
                raise RuntimeError(f'返回字幕无时间戳，无法使用')
        tmp = transcript.split("----..----")
        if len(tmp) == 1 or not config.settings['rephrase']:
            raws = tools.get_subtitle_from_srt(tmp[0], is_file=False)
        else:
            try:
                ## transcript='src字符串----..----[{'start': 2.34, 'end': 3.04, 'word': ' there'},...]'
                words_list = json.loads(tmp[-1].strip())
                raws = self.re_segment_sentences(words_list)
            except:
                config.logger.info(f'重新断句失败')
                raws = tools.get_subtitle_from_srt(tmp[0], is_file=False)

        return raws
