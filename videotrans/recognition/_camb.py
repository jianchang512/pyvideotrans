import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr, params, settings, app_cfg, logger, ROOT_DIR
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


def _get_camb_lang_id(langcode):
    """Map pyvideotrans language code to CAMB AI integer language ID."""
    cache_file = Path(ROOT_DIR + '/videotrans/voicejson/camb_languages.json')
    if cache_file.exists():
        mapping = json.loads(cache_file.read_text(encoding='utf-8'))
        if langcode in mapping:
            return mapping[langcode]
        prefix = langcode.split('-')[0] if '-' in langcode else langcode
        if prefix in mapping:
            return mapping[prefix]
    return None


@dataclass
class CambRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        lang_id = _get_camb_lang_id(self.detect_language)
        if not lang_id:
            # Try to refresh language cache
            from videotrans.translator._camb import refresh_camb_languages
            refresh_camb_languages()
            lang_id = _get_camb_lang_id(self.detect_language)
        if not lang_id:
            lang_id = 1  # Default to English

        self._signal(text=tr("Recognition may take a while, please be patient"))

        try:
            from camb.client import CambAI
            client = CambAI(
                api_key=params.get('camb_api_key', '') or os.environ.get('CAMB_API_KEY', ''),
                httpx_client=httpx.Client(proxy=self.proxy_str) if self.proxy_str else None
            )
            print(f'{self.audio_file=}')

            # Submit transcription job
            create_result = client.transcription.create_transcription(
                language=lang_id,
                media_file=open(self.audio_file,'rb'),
            )

            task_id = create_result.task_id

            # Poll for completion
            max_wait = 600  # 10 minutes max
            poll_interval = 3
            elapsed = 0
            while elapsed < max_wait:
                status_result = client.transcription.get_transcription_task_status(task_id)
                status = status_result.status if hasattr(status_result, 'status') else status_result.get('status', '')

                if status == 'SUCCESS':
                    break
                elif status == 'ERROR':
                    err_msg = status_result.exception_reason if hasattr(status_result, 'exception_reason') else status_result.get('exception_reason', 'Unknown error')
                    raise RuntimeError(f"CAMB AI transcription failed: {err_msg}")

                if self._exit():
                    return

                time.sleep(poll_interval)
                elapsed += poll_interval
                self._signal(text=f"Transcribing... ({elapsed}s)")

            if elapsed >= max_wait:
                raise RuntimeError("CAMB AI transcription timed out")

            # Get results
            run_id = status_result.run_id if hasattr(status_result, 'run_id') else status_result.get('run_id')
            transcription_result = client.transcription.get_transcription_result(run_id)

            # Parse transcript entries
            transcript = transcription_result.transcript if hasattr(transcription_result, 'transcript') else transcription_result.get('transcript', [])

            raws = []
            speaker_list = []
            diarize = self.max_speakers > -1

            for entry in transcript:
                start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
                end = entry.end if hasattr(entry, 'end') else entry.get('end', 0)
                text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
                speaker = entry.speaker if hasattr(entry, 'speaker') else entry.get('speaker', '')

                if not text.strip():
                    continue

                start_ms = int(start * 1000)
                end_ms = int(end * 1000)

                tmp = {
                    "line": len(raws) + 1,
                    "start_time": start_ms,
                    "end_time": end_ms,
                    "text": text.strip()
                }

                if self.detect_language and self.detect_language[:2] in ['zh', 'ja', 'ko']:
                    tmp['text'] = re.sub(r'\s| ', '', tmp['text'], flags=re.I | re.S)

                tmp['time'] = tools.ms_to_time_string(ms=start_ms) + ' --> ' + tools.ms_to_time_string(ms=end_ms)
                tmp['startraw'] = tools.ms_to_time_string(ms=start_ms)
                tmp['endraw'] = tools.ms_to_time_string(ms=end_ms)

                raws.append(tmp)

                if diarize and speaker:
                    speaker_list.append(f'[{speaker}]')

            if diarize and speaker_list:
                Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')

            return raws

        except Exception as e:
            err_str = str(e)
            if '401' in err_str or '403' in err_str or 'Unauthorized' in err_str:
                raise StopRetry(err_str)
            raise
