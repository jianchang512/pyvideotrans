import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from gradio_client import Client, handle_file
from videotrans.configure.config import tr, params, settings, app_cfg, logger, ROOT_DIR
from videotrans.configure._except import  StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class OmniVoice(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = params.get('omnivoice_url','').strip().rstrip('/').lower()
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item,idx:int=-1):
        text = data_item['text'].strip()
        if self._exit() or  not text or tools.vail_file(data_item['filename']):
            return

        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        role = data_item['role']
        ref_aud=''
        ref_text=data_item.get('ref_text','')
        
        rolelist = tools.get_omnivoice_role()

        if role not in rolelist:
            raise StopRetry(tr('The role {} does not exist',role))
        if role == 'clone':
            ref_aud = data_item.get('ref_wav','')
            ref_text = data_item.get('ref_text','')
        else:
            ref_aud = ROOT_DIR+"/f5-tts/"+rolelist[role].get('reference_audio','')
            ref_text = rolelist[role].get('reference_text','')

        if not Path(ref_aud).exists():
            raise StopRetry(f"{ref_aud} is not exists")
        
        logger.debug(f'omnivoice-tts {ref_aud=},{ref_text=}')
        try:
            client = Client(self.api_url, ssl_verify=False)
        except Exception as e:
            raise StopRetry(str(e))
        lang=self.language.split('-')[0]
        result = client.predict(
            text=text,
            lang='Auto',
            ref_aud=handle_file(ref_aud),
            ref_text=ref_text,
            instruct='',
            ns=32,
            gs=2.0,
            dn=True,
            sp=speed,
            du=0,
            pp=True,
            po=True,
            api_name="/_clone_fn",
        )


        logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))



