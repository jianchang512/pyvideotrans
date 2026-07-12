import logging
from dataclasses import dataclass
from typing import Union, Dict, List

import requests
from gradio_client import handle_file
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import settings, logger,tr
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.tts._gradio import GradioBase

@dataclass
class ConfuciusTTS(GradioBase):
    def __post_init__(self):
        self.ainame="confuciustts"
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "text":data_item.get('text',''),
            "lang":self.language.split('-')[0],
            "ref_aud":handle_file(ref_wav),
            "api_name":"/_clone_fn",
        }
        return self._send(kwargs, data_item)
    
    
    