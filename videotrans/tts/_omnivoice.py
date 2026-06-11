import logging
from dataclasses import dataclass
from typing import Union, Dict, List

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import params, settings, logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS


@dataclass
class OmniVoice(BaseTTS):
    """OmniVoice Studio TTS/clone channel (REST).

    OmniVoice Studio (https://github.com/debpalash/OmniVoice-Studio) is a
    FastAPI desktop app — its default API listens on http://127.0.0.1:3900.
    This channel POSTs ``/generate`` per subtitle line (multipart): the line
    text plus the per-line reference wav + transcript for voice cloning, and
    receives WAV bytes back. Replaces the previous gradio_client integration,
    which targeted a ``/_clone_fn`` Gradio endpoint that current OmniVoice
    Studio builds do not expose (the app is FastAPI-only).

    OmniVoice Studio pins this request shape with a contract test on their
    side (tests/test_pyvideotrans_contract.py), so the surface used here is
    guaranteed by their CI.
    """

    def __post_init__(self):
        self.ainame = "omnivoice"
        # ISO code -> natural-language name (OmniVoice accepts language
        # names; "Auto" lets it detect from text).
        lang_code = {
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
            "yue": "Cantonese",
        }
        self.lang = lang_code.get(self.language, 'Auto') if self.language else 'Auto'
        super().__post_init__()
        self.api_url = (params.get('omnivoice_url', '') or 'http://127.0.0.1:3900').strip().rstrip('/')
        if not self.api_url.startswith('http'):
            self.api_url = 'http://' + self.api_url
        if len(self.api_url) < 10:
            raise StopTask(f'OmniVoice API URL is error: {self.api_url}')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav, ref_text = self.get_ref_wav(data_item)

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
