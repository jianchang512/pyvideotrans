import logging
from dataclasses import dataclass
from typing import Union, Dict, List

from gradio_client import handle_file
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import settings, logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.tts._gradio import GradioBase

@dataclass
class OmniVoice(GradioBase):
    def __post_init__(self):
        self.ainame="omnivoice"
        # 语言代码 对应语言名称
        lang_code={
            "en": "English",
            "zh": "Chinese",
            "zh-cn": "Chinese",
            "zh-tw": "Min Nan Chinese",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "es": "Spanish",
            "el": "Greek",
            "nb": "Norwegian Bokmål",
            "km": "Khmer",
            "th": "Thai",
            "it": "Italian",
            "pt": "Portuguese",
            "vi": "Vietnamese",
            "ar": "Standard Arabic",
            "tr": "Turkish",
            "hi": "Hindi",
            "hu": "Hungarian",
            "uk": "Ukrainian",
            "id": "Indonesian",
            "ms": "Malay",
            "kk": "Kazakh",
            "cs": "Czech",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "he": "Hebrew",
            "bn": "Bengali",
            "fa": "Persian",
            "fil": "Filipino",
            "ur": "Urdu",
            "yue": "Cantonese"
        }
        self.lang=lang_code.get(self.language,'Auto') if self.language else 'Auto'
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:

        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "text":data_item.get('text',''),
            "lang":self.lang,
            "ref_aud":handle_file(ref_wav),
            "ref_text":ref_text,
            "instruct":'',
            "ns":32,
            "gs":2.0,
            "dn":False,
            "sp":self.get_speed(),
            "du":0,
            "pp":True,
            "po":False,
            "api_name":"/_clone_fn",
        }
        return self._send(kwargs, data_item)
