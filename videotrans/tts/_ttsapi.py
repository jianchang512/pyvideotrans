import copy
import sys
from pathlib import Path
from typing import Union, Dict, List
from urllib.parse import urlparse

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
        self.proxies=None

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
                    "language": self.language[:2] if self.language else "",
                    "extra": config.params['ttsapi_extra'],
                    "voice": role,
                    "ostype": sys.platform,
                    "rate": 0}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            }
            config.logger.info(f'发送数据 {data=}')
            resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers,proxies=None)
            if resraw.status_code != 200:
                self.error = f'TTS-API:{resraw.status_code} {resraw.reason}'
                return
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
            # 返回的是音频url地址
            if res['data'].startswith('http'):
                url = res['data']
                res = requests.get(url)
                if res.status_code != 200:
                    self.error = f'{url=}'
                    return

                tmp_filename=data_item['filename']
                try:
                    # 如果url指向的音频不是mp3，则需要转为mp3
                    url_ext=Path(urlparse(url).path.rpartition('/')[-1]).suffix.lower()
                except Exception:
                    url_ext='.mp3'
                else:
                    if url_ext!='.mp3':
                        tmp_filename+=f'{url_ext}'
                with open(tmp_filename, 'wb') as f:
                    f.write(res.content)
                if url_ext!='.mp3':
                    tools.runffmpeg([
                        "-y","-i",tmp_filename,data_item['filename']
                    ])
            elif res['data'].startswith('data:audio'):
                # 返回 base64数据
                self._base64_to_audio(res['data'],data_item['filename'])
            else:
                raise Exception('未返回有效音频地址或音频base64数据' if config.defaulelang == 'zh' else 'No valid audio address or base64 audio data returned')
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
