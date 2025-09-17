import os
import logging
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class FishTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        api_url = config.params['fishtts_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            role = data_item['role']
            roledict = tools.get_fishtts_role()
            if not role or not roledict.get(role):
                raise StopRetry('必须在设置中填写参考音频路径名、参考音频对应的文字')

            if self._exit() or tools.vail_file(data_item['filename']):
                return

            data = {"text": data_item['text'],
                    "references": [{"audio": "", "text": roledict[role]['reference_text']}]}

            # 克隆声音
            audio_path = f'{config.ROOT_DIR}/{roledict[role]["reference_audio"]}'
            if os.path.exists(audio_path):
                data['references'][0]['audio'] = self._audio_to_base64(audio_path)
            else:
                raise StopRetry(f'参考音频不存在:{audio_path}\n请确保该音频存在')

            config.logger.info(f'fishTTS-post:{data=},{self.proxies=}')
            response = requests.post(f"{self.api_url}", json=data, proxies=self.proxies, timeout=3600)

            response.raise_for_status()

            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                time.sleep(RETRY_DELAY)
                raise RuntimeError(f'FishTTS合成声音失败-2')
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error = e
