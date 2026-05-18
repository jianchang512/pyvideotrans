import json
import logging
import os
from dataclasses import dataclass
from typing import Union, List, Dict
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, ROOT_DIR, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from camb.client import CambAI
from camb.types.stream_tts_output_configuration import StreamTtsOutputConfiguration

# Map pyvideotrans language codes to CAMB AI locale strings
LANG_TO_CAMB_LOCALE = {
    "en": "en-us",
    "zh-cn": "zh-cn",
    "zh-tw": "zh-tw",
    "fr": "fr-fr",
    "de": "de-de",
    "ja": "ja-jp",
    "ko": "ko-kr",
    "ru": "ru-ru",
    "es": "es-es",
    "th": "th-th",
    "it": "it-it",
    "pt": "pt-pt",
    "vi": "vi-vn",
    "ar": "ar-sa",
    "tr": "tr-tr",
    "hi": "hi-in",
    "hu": "hu-hu",
    "uk": "uk-ua",
    "id": "id-id",
    "ms": "ms-my",
    "cs": "cs-cz",
    "pl": "pl-pl",
    "nl": "nl-nl",
    "sv": "sv-se",
    "he": "he-il",
    "bn": "bn-bd",
    "fa": "fa-ir",
    "fil": "fil-ph",
    "ur": "ur-pk",
    "yue": "zh-hk",
}


@dataclass
class CambTTS(BaseTTS):

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = data_item['role']
        # Determine locale
        locale = LANG_TO_CAMB_LOCALE.get(self.language, LANG_TO_CAMB_LOCALE.get(self.language[:2], "en-us"))

        # Load voice data
        jsonfile = ROOT_DIR + '/videotrans/voicejson/camb.json'
        voice_id = None
        if os.path.exists(jsonfile):
            with open(jsonfile, 'r', encoding='utf-8') as f:
                jsondata = json.loads(f.read())
            if role in jsondata:
                voice_id = jsondata[role].get('id')

        # Handle clone mode
        if role == 'clone' and data_item.get('ref_wav'):
            voice_id = self._get_or_create_clone_voice(data_item['ref_wav'])
            if not voice_id:
                return "Failed to create cloned voice from reference audio"

        client = CambAI(
            api_key=params.get('camb_api_key', '') or os.environ.get('CAMB_API_KEY', ''),
            httpx_client=httpx.Client(proxy=self.proxy_str) if self.proxy_str else None
        )

        # voice_id is required by the CAMB AI API
        if not voice_id:
            # Get first available voice as default
            voices = client.voice_cloning.list_voices()
            if voices:
                first = voices[0]
                voice_id = first.id if hasattr(first, 'id') else first.get('id')
            if not voice_id:
                return "No voices available. Please configure a voice in CAMB AI TTS settings."

        tts_kwargs = {
            "text": data_item['text'],
            "language": locale,
            "voice_id": voice_id,
            "speech_model": params.get('camb_speech_model', 'mars-flash'),
            "output_configuration": StreamTtsOutputConfiguration(format="mp3"),
        }

        response = client.text_to_speech.tts(**tts_kwargs)

        with open(data_item['filename'] + ".mp3", 'wb') as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])



    def _get_or_create_clone_voice(self, ref_wav):
        """Upload reference audio to create a cloned voice, caching the voice_id."""
        cache_key = f'camb_clone_{tools.get_md5(ref_wav)}'
        cached_id = params.get(cache_key)
        if cached_id:
            return cached_id

        try:
            from camb.client import CambAI
            client = CambAI(
                api_key=params.get('camb_api_key', '') or os.environ.get('CAMB_API_KEY', ''),
                httpx_client=httpx.Client(proxy=self.proxy_str) if self.proxy_str else None
            )
            result = client.voice_cloning.create_custom_voice(
                voice_name=f"clone_{os.path.basename(ref_wav)}",
                gender=1,
                file=ref_wav,
                enhance_audio=True,
            )
            voice_id = result.voice_id
            params[cache_key] = voice_id
            return voice_id
        except Exception as e:
            logger.exception(f'CAMB AI voice cloning failed: {e}', exc_info=True)
            return None


