import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union, List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.configure.config import tr, params, logger, ROOT_DIR, settings
from videotrans.tts._base import BaseTTS
from videotrans.util import tools



@dataclass
class MossTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        service_urls = tools.get_mosstts_service_urls(params.get('moss_tts_url', ''))
        self.api_url = service_urls['generate_url']
        self.service_root = service_urls['service_root']
        self.roledict = tools.get_f5tts_role()

    def _get_demo_id(self, role_name: str):
        role_map = tools.get_mosstts_demo_map()
        if role_name in role_map:
            return role_map[role_name].get('demo_id')
        return None


    def _write_response_audio(self, audio_base64: str, out_file: str):
        temp_file = f'{out_file}.moss.wav'
        Path(temp_file).write_bytes(base64.b64decode(audio_base64))
        self.convert_to_wav(temp_file, out_file)
        Path(temp_file).unlink(missing_ok=True)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        payload = {
            'text': data_item['text'].strip(),
            'enable_text_normalization': '1',
        }
        role = str(data_item.get('role') or 'No').strip()
        if role == 'No':
            return 'Please select role for TTS'
        response = None

        if role == 'clone':
            ref_wav = data_item.get('ref_wav')
            if not ref_wav or not Path(ref_wav).is_file():
                return tr("No reference audio exists and cannot use clone function")
            with open(ref_wav, 'rb') as file_obj:
                response = requests.post(
                    self.api_url,
                    data=payload,
                    files={'prompt_audio': file_obj},
                    timeout=3600,
                )
        else:
            local_ref_wav = self.roledict.get(role,{}).get('ref_wav')
            if local_ref_wav and Path(f'{ROOT_DIR}/f5-tts/{local_ref_wav}').is_file():
                with open(f'{ROOT_DIR}/f5-tts/{local_ref_wav}', 'rb') as file_obj:
                    response = requests.post(
                        self.api_url,
                        data=payload,
                        files={'prompt_audio': file_obj},
                        timeout=3600,
                    )
            else:
                demo_id = self._get_demo_id(role)
                if not demo_id:
                    return tr('The role {} does not exist', role)
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
            return str(result)
        self._write_response_audio(audio_base64, data_item['filename'])
