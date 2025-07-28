import copy
import time
from pathlib import Path

import requests

from videotrans import tts
from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


class AI302(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.proxies = None

    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                if data_item['role'] not in tts.DOUBAO_302AI:
                    self._azure(data=data_item)
                else:
                    data_item['role'] = tts.DOUBAO_302AI[data_item['role']]
                    self._doubao(data=data_item)
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except (requests.ConnectionError, requests.exceptions.ProxyError,requests.Timeout, requests.exceptions.RetryError) as e:
                config.logger.exception(e,exc_info=True)
                # 中文和英文
                self.error = '连接失败，请尝试使用或切换代理' if config.defaulelang == 'zh' else 'Connect  failed, please try to use or switch proxy'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                config.logger.exception(e,exc_info=True)
                self.error = str(e)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)

    def _azure(self, data):
        ssml = f"""<speak version='1.0' xml:lang='{data["role"][:5]}'>
        <voice name='{data["role"]}' lang='{data["role"][:5]}'>            
            <prosody rate="{self.rate}" pitch='{self.pitch}'  volume='{self.volume}'>
            {data["text"]}
            </prosody>
        </voice>
        </speak>"""
        # Riff48Khz16BitMonoPcm
        headers = {
            'Authorization': f'Bearer {config.params["ai302_key"]}',
            'X-Microsoft-OutputFormat': 'riff-48khz-16bit-mono-pcm',
            'Content-Type': 'application/ssml+xml'
        }
        response = requests.post('https://api.302.ai/cognitiveservices/v1',
                                 headers=headers,
                                 data=ssml,
                                 verify=False, proxies=None)
        response.raise_for_status()
        # wav 需转为mp3
        with open(data['filename'] + ".wav", 'wb') as f:
            f.write(response.content)
        tools.wav2mp3(data['filename'] + ".wav", data['filename'])
        Path(data['filename'] + ".wav").unlink(missing_ok=True)

    def _doubao(self, data):
        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        payload = {
            "audio": {
                "voice_type": data['role'],
                "encoding": "mp3",
                "speed_ratio": speed
            },
            "request": {
                "reqid": f'pyvideotrans-{time.time()}',
                "text": data['text'],
                "operation": "query"
            }
        }
        response = requests.post('https://api.302.ai/doubao/tts_hd', headers={
            'Authorization': f'Bearer {config.params["ai302_key"]}',
            'User-Agent': 'pyvideotrans',
            'Content-Type': 'application/json'
        }, json=payload, verify=False, proxies=None)
        response.raise_for_status()
        res = response.json()
        if res['code'] != 3000:
            raise RuntimeError(f"{res['code']}:{res['message']}")
        self._base64_to_audio(res['data'], data['filename'])
