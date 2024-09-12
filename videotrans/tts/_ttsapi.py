import copy
import sys
from typing import Union, Dict, List

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发

class TTSAPI(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['ttsapi_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

    def _exec(self) -> None:
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            text = data_item['text'].strip()
            role = data_item['role']
            if not text:
                return
            data = {"text": text.strip(),
                    # "language": self.language,
                    "extra": config.params['ttsapi_extra'],
                    "voice": role,
                    "ostype": sys.platform,
                    "rate": 0}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            }
            config.logger.info(f'发送数据 {data=}')
            resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers)
            res = resraw.json()
            config.logger.info(f'返回数据 {res=}')
            if "code" not in res or "msg" not in res:
                self.error = f'TTS-API:{res}'
                return
            if res['code'] != 0:
                self.error = f'TTS-API:{res["msg"]}'
                return
            if 'data' not in res or not res['data']:
                raise Exception('未返回有效音频地址' if config.defaulelang == 'zh' else 'No valid audio address returned')
            url = res['data']
            res = requests.get(url)
            if res.status_code != 200:
                self.error = f'{url=}'
                return
            with open(data_item['filename'], 'wb') as f:
                f.write(res.content)
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
        except requests.ConnectionError as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
