import copy
import re
import time
from pathlib import Path

import requests
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发 返回wav数据，转为mp3

class KokoroTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_url = config.params['kokoro_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        if not self.api_url.endswith('/v1/audio/speech'):
            self.api_url+='/v1/audio/speech'
        self.proxies={"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit():
            return
        if not data_item:
            return
        try:
            text = data_item['text'].strip()
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate
            data = {"input": text, "voice": data_item['role'],"speed":speed}

            res = requests.post(self.api_url, json=data, proxies=self.proxies, timeout=3600)
            res.raise_for_status()

            with open(data_item['filename'], 'wb') as f:
                f.write(res.content)
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
        except (requests.ConnectionError, requests.Timeout) as e:
            self.error="连接失败，请检查是否启动了api服务" if config.defaulelang=='zh' else  'Connection failed, please check if the api service is started'
        except Exception as e:
            Path(data_item['filename']).unlink(missing_ok=True)
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
