import base64
import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr, params, logger
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class MossTTS(BaseTTS):
    splits: set[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…"}
        service_urls = tools.get_mosstts_service_urls(params.get('moss_tts_url', ''))
        self.api_url = service_urls['generate_url']
        self.service_root = service_urls['service_root']
        self._add_internal_host_noproxy(self.service_root or self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _get_demo_id(self, role_name: str):
        role_map = tools.get_mosstts_demo_map()
        if role_name in role_map:
            return role_map[role_name].get('demo_id')
        return None

    def _get_local_ref_wav(self, role_name: str):
        role_map = tools.get_mosstts_local_role_map()
        if role_name in role_map:
            return role_map[role_name].get('audio_path')
        return None

    def _write_response_audio(self, audio_base64: str, out_file: str):
        temp_file = f'{out_file}.moss.wav'
        Path(temp_file).write_bytes(base64.b64decode(audio_base64))
        self.convert_to_wav(temp_file, out_file)
        Path(temp_file).unlink(missing_ok=True)

    def _item_task(self, data_item: dict = None, idx: int = -1):
        if self._exit() or not data_item.get('text', '').strip():
            return

        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
               after=after_log(logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            text = data_item['text'].strip()
            if text[-1] not in self.splits:
                text += '.'

            payload = {
                'text': text,
                'enable_text_normalization': '1',
            }
            role = str(data_item.get('role', 'No') or 'No').strip()
            role_lower = role.lower()
            response = None

            if role_lower == 'clone':
                ref_wav = data_item.get('ref_wav')
                if not ref_wav or not Path(ref_wav).is_file():
                    raise StopRetry(tr("No reference audio exists and cannot use clone function"))
                with open(ref_wav, 'rb') as file_obj:
                    response = requests.post(
                        self.api_url,
                        data=payload,
                        files={'prompt_audio': file_obj},
                        timeout=3600,
                    )
            else:
                local_ref_wav = self._get_local_ref_wav(role)
                if local_ref_wav and Path(local_ref_wav).is_file():
                    with open(local_ref_wav, 'rb') as file_obj:
                        response = requests.post(
                            self.api_url,
                            data=payload,
                            files={'prompt_audio': file_obj},
                            timeout=3600,
                        )
                else:
                    demo_id = self._get_demo_id(role)
                    if not demo_id:
                        raise StopRetry(tr('The role {} does not exist', role))
                    payload['demo_id'] = demo_id
                    response = requests.post(
                        self.api_url,
                        data=payload,
                        timeout=3600,
                    )

            response.raise_for_status()
            result = response.json()
            audio_base64 = result.get('audio_base64', '')
            if not audio_base64:
                raise RuntimeError(str(result))
            self._write_response_audio(audio_base64, data_item['filename'])

        try:
            _run()
        except Exception as e:
            self.error = e
            raise