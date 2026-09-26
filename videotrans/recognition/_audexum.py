# Audexum speech-to-text (https://audexum.com), OpenAI-compatible endpoint
import os
import time
from dataclasses import dataclass
from typing import List, Union

import httpx
from openai import OpenAI, APIConnectionError, APIStatusError

from videotrans.configure.config import params, logger, tr
from videotrans.configure.excepts import StopTask
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem

AUDEXUM_BASE_URL = "https://audexum.com/v1"
AUDEXUM_KEY_URL = "https://audexum.com/developer?ref=gh-pyvideotrans"
AUDEXUM_TOPUP_URL = "https://audexum.com/pricing?ref=gh-pyvideotrans"


def _error_code(e: APIStatusError) -> str:
    # Audexum returns {"detail": {"error": "insufficient_credits", ...}} or {"detail": "no_speech_detected"}
    body = e.body if isinstance(e.body, dict) else {}
    detail = body.get("detail", body)
    if isinstance(detail, dict):
        return str(detail.get("error", ""))
    return str(detail or "")


@dataclass
class AudexumRecogn(BaseRecogn):

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        api_key = params.get('audexum_key', '')
        if not api_key:
            raise StopTask(tr("api key must be filled in"))
        client = OpenAI(api_key=api_key, base_url=AUDEXUM_BASE_URL,
                        http_client=httpx.Client(proxy=self.proxy_str or None))
        language = self.detect_language.split('-')[0] if self.detect_language and self.detect_language != 'auto' else None
        raws = self.cut_audio()
        try:
            for it in raws:
                if self._exit(): return
                with open(it['filename'], 'rb') as f:
                    kwargs = dict(file=(os.path.basename(it['filename']), f.read()),
                                  model='whisper-1', response_format='json')
                if language:
                    kwargs['language'] = language
                try:
                    transcript = client.audio.transcriptions.create(**kwargs)
                except APIStatusError as e:
                    # a VAD clip that is only noise: skip it, keep the rest of the job
                    if e.status_code == 400 and _error_code(e) in ('no_speech_detected', 'audio_too_short'):
                        logger.warning(f'Audexum skipped {it["filename"]}: {_error_code(e)}')
                        continue
                    raise
                it['text'] = (getattr(transcript, 'text', '') or '').strip()
                if self.asr_wait > 0:
                    time.sleep(self.asr_wait)
        except APIConnectionError as e:
            raise StopTask(f'{tr("Unable to connect to API", AUDEXUM_BASE_URL)}\n{e}') from e
        except APIStatusError as e:
            if e.status_code == 401:
                raise StopTask(tr("Audexum: the API key is invalid. Get a key at {}", AUDEXUM_KEY_URL)) from e
            if e.status_code == 402 or _error_code(e) == 'stt_quota_exceeded':
                raise StopTask(tr("Audexum: not enough credits for this audio. Top up at {}", AUDEXUM_TOPUP_URL)) from e
            raise
        return [it for it in raws if it['text']]
