import os
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from gradio_client import Client, handle_file, client

from videotrans import translator
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class QwenttsLocal(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params.get('qwenttslocal_url', '').strip().rstrip('/').lower()
        self.prompt = config.params.get('qwenttslocal_prompt', '')
        self.roledict = tools.get_qwenttslocal_rolelist()
        self.client = Client(self.api_url,httpx_kwargs={"timeout":7200})

        self.custom_voice = ["Vivian",
                             "Serena",
                             "Uncle_fu",
                             "Dylan",
                             "Eric",
                             "Ryan",
                             "Aiden",
                             "Ono_anna",
                             "Sohee"
                             ]
        _langnames = translator.LANG_CODE.get(self.language, [])
        if _langnames and len(_langnames) >= 10:
            self.target_language = _langnames[9]
        else:
            self.target_language = 'Auto'
        self.target_language=self.target_language.capitalize()
        print(f'{self.target_language=}')
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item):

        if data_item['role'] in self.custom_voice:
            return self._customevoice(data_item)
        return self._clone(data_item)

    # 使用预定义角色+prompt
    def _customevoice(self, data_item):

        text = data_item['text'].strip()
        if not text:
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass
        speed = max(0.5, min(2.0, speed))
        role = data_item['role']

        result = self.client.predict(
            text=text,
            lang_disp=self.target_language,
            spk_disp=role,
            instruct=self.prompt,
            #model_size=config.params.get('qwenttslocal_size', '1.7B'),
            api_name="/run_instruct",
        )
        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))

    # 使用视频中原语音或本地参考音频
    def _clone(self, data_item):
        text = data_item['text'].strip()
        if not text:
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass
        speed = max(0.5, min(2.0, speed))
        role = data_item['role']
        # 视频中语音克隆，存在参考音频
        if role == 'clone':
            wavfile = data_item.get('ref_wav', '')
            ref_text = data_item.get('ref_text', '')
        else:
            # 使用 f5-tts文件夹内音频
            wavfile = f'{config.ROOT_DIR}/f5-tts/{role}'
            ref_text = self.roledict.get(role, '')
        print(f'{self.roledict=}')
        if not wavfile or not Path(wavfile).is_file():
            # 仍然不存在，无参考音频不可用
            self.error = f"不存在参考音频，无法克隆:{role=},{wavfile=}"
            config.logger.error(self.error)
            return

        result = self.client.predict(
            ref_aud=handle_file(wavfile),
            ref_txt=ref_text,
            text=text,
            lang_disp=self.target_language,
            use_xvec=False if ref_text else True,            
            #model_size=config.params.get('qwenttslocal_size', '1.7B'),
            api_name="/run_voice_clone",
            
        )

        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))
