import re
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class CloneVoice(BaseTTS):
    splits: Set[str] = field(init=False)

    def __post_init__(self):

        super().__post_init__()
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…"}

        api_url = config.params.get('clone_api', '').strip().rstrip('/').lower()
        # 确保即使 api_url 为空也不会出错
        if api_url:
            self.api_url = 'http://' + api_url.replace('http://', '')

        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if data_item['text'][-1] not in self.splits:
                data_item['text'] += '.'
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            data = {"text": data_item['text'], "language": self.language}
            role = data_item['role']
            if role != 'clone':
                # 不是克隆，使用已有声音
                data['voice'] = role
                files = None
            else:
                if not Path(data_item['ref_wav']).exists():
                    self.error = f'不存在参考音频，无法使用clone功能' if config.defaulelang == 'zh' else 'No reference audio exists and cannot use clone function'
                    raise RuntimeError(self.error)
                with open(data_item['ref_wav'], 'rb') as f:
                    chunk = f.read()
                files = {"audio": chunk}
            res = requests.post(f"{self.api_url}/apitts", data=data, files=files, proxies=self.proxies,
                                timeout=3600)
            res.raise_for_status()
            config.logger.info(f'clone-voice:{data=},{res.text=}')
            res = res.json()
            if "code" not in res or res['code'] != 0:
                if "msg" in res and res['msg'].find("non-empty") > 0:
                    Path(data_item['filename']).unlink(missing_ok=True)
                self.error = f'{res}'
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                self.convert_to_wav(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return

            resb = requests.get(res['url'], proxies=self.proxies)
            resb.raise_for_status()
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resb.content)
            time.sleep(1)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
