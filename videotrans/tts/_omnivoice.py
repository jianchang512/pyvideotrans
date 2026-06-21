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
class OmniVoice(GradioBase):
    def __post_init__(self):
        self.ainame="omnivoice"
        # 语言代码 对应语言名称
        lang_code= {
            "zh-cn": "Chinese",
            "zh-tw": "Min Nan Chinese",
            "zh": "Chinese",
            "yue": "Cantonese",
            "en": "English",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "es": "Spanish",
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
            "fil": "Filipino",

            "af": "Afrikaans",
            "sq": "Albanian",
            "am": "Amharic",
            "az": "Azerbaijani",
            "bs": "Bosnian",
            "bg": "Bulgarian",
            "my": "Burmese",
            "ca": "Catalan",
            "hr": "Croatian",
            "da": "Danish",
            "et": "Estonian",
            "fi": "Finnish",
            "gl": "Galician",
            "ka": "Georgian",
            "el": "Greek",
            "gu": "Gujarati",
            "is": "Icelandic",
            "iu": "Inuktitut",
            "ga": "Irish",
            "jv": "Javanese",
            "kn": "Kannada",
            "km": "Khmer",
            "lo": "Lao",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mk": "Macedonian",
            "ml": "Malayalam",
            "mt": "Maltese",
            "mr": "Marathi",
            "mn": "Mongolian",
            "ne": "Nepali",
            "nb": "Norwegian Bokmål",
            "ps": "Pashto",
            "fa": "Persian",

            "ro": "Romanian",
            "sr": "Serbian",
            "si": "Sinhala",
            "sk": "Slovak",
            "sl": "Slovenian",
            "so": "Somali",
            "su": "Sudanese Arabic",
            "sw": "Swahili",
            "ta": "Tamil",
            "te": "Telugu",
            "ur": "Urdu",
            "uz": "Uzbek",
            "cy": "Welsh",
            "zu": "Zulu"
        }
        self.lang=lang_code.get(self.language,'Auto') if self.language else 'Auto'
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if self.api_url.endswith(':3900'):#OmniVoice-studio
            return self._omnivoice_studio(data_item)
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
    
    
    def _omnivoice_studio(self,data_item):
        ref_wav,ref_text = self.get_ref_wav(data_item)
        data = {
            "text": data_item.get('text', ''),
            "language": self.lang,
            "num_step": 32,
            "guidance_scale": 2.0,
            "speed": self.get_speed(),
            "denoise": "false",
            "postprocess_output": "true",
        }
        files = None
        if ref_wav:
            files = {"ref_audio": open(ref_wav, 'rb')}
            if ref_text:
                data["ref_text"] = ref_text

        logger.debug(f'OmniVoice request: {self.api_url=}/generate {data=}')
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                data=data,
                files=files,
                timeout=3600,
                proxies={"https": "", "http": ""},
            )
        finally:
            if files:
                files["ref_audio"].close()

        if not response.ok:
            error_data = response.text + f"\n{self.api_url=}"
            logger.error(f'OmniVoice returned error: {error_data=}')
            return error_data

        with open(data_item['filename'] + ".wav", 'wb') as f:
            f.write(response.content)
        self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])