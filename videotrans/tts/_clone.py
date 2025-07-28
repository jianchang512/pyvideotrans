import copy
import re
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


class CloneVoice(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['clone_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):

        if data_item['text'][-1] not in self.splits:
            data_item['text'] += '.'
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                data = {"text": data_item['text'], "language": self.language}
                role = data_item['role']
                if role != 'clone':
                    # 不是克隆，使用已有声音
                    data['voice'] = role
                    files = None
                else:
                    if not Path(data_item['ref_wav']).exists():
                        self.error = f'不存在参考音频，无法使用clone功能' if config.defaulelang == 'zh' else 'No reference audio exists and cannot use clone function'
                        return
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
                    continue

                if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                    tools.wav2mp3(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
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
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
                Path(data_item['filename'] + ".wav").unlink(missing_ok=True)
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except (requests.ConnectionError, requests.Timeout) as e:
                config.logger.exception(e,exc_info=True)
                self.error = "连接失败，请检查是否启动了api服务" if config.defaulelang == 'zh' else 'Connection failed, please check if the api service is started'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                self.error = str(e)
                config.logger.exception(e, exc_info=True)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}:"+self.error)
                time.sleep(RETRY_DELAY)
