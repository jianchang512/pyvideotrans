import re
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatTTS(BaseTTS):

    def __post_init__(self):

        super().__post_init__()

        # 从配置中读取并处理 API URL
        api_url = config.params['chattts_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '').replace('/tts', '')

        # 为代理设置一个具体的值
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            data = {"text": data_item['text'], "voice": data_item['role'], 'prompt': '', 'is_split': 1}
            res = requests.post(f"{self.api_url}/tts", data=data, proxies=self.proxies, timeout=3600)
            res.raise_for_status()
            config.logger.info(f'chatTTS:{data=}')
            res = res.json()
            if res is None:
                self.error = 'ChatTTS端出错，请查看其控制台终端'
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            if "code" not in res or res['code'] != 0:
                if "msg" in res:
                    Path(data_item['filename']).unlink(missing_ok=True)
                self.error = f'{res}'
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                self.convert_to_wav(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.has_done += 1
                self.error = ''
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return

            resb = requests.get(res['url'])
            resb.raise_for_status()

            config.logger.info(f'ChatTTS:resb={resb.status_code=}')
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resb.content)
            time.sleep(1)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self.error = ''
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
            return

        _run()
