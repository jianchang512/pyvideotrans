import copy
import json
import time
from pathlib import Path

import requests

from videotrans import tts
from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5

from dataclasses import dataclass, field

@dataclass
class AI302(BaseTTS):
    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                self._generate(data=data_item)
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


    def _generate(self, data):
        speed = 1.0
        volume = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        if self.volume:
            volume += float(self.volume.replace('%', '')) / 100
        payload = {
            "model": "",
            "provider":"",
            "input":data['text'],
            "voice": data['role'],
            "output_format":"mp3",
            "speed":speed,
            "volume":volume
        }
        if data['role'] in tts.AI302_doubao or data['role'] in tts.AI302_doubao_ja:
            payload['provider']='doubao'
        elif data['role'] in tts.AI302_minimaxi:
            payload['provider']='minimaxi'
            payload['model']='speech-02-hd'
        elif data['role'] in tts.AI302_dubbingx:
            payload['provider']='dubbingx'
        elif data['role'] in tts.AI302_openai:
            payload['provider']='openai'
            payload['model']='gpt-4o-mini-tts'
        else:
            payload['provider']='azure'
        response = requests.post('https://api.302.ai/doubao/tts_hd', headers={
            'Authorization': f'Bearer {config.params["ai302_key"]}',
            'Content-Type': 'application/json'
        }, data=json.dumps(payload), verify=False, proxies=None)
        response.raise_for_status()
        res = response.json()

        audio_url=res.get("audio_url")
        if  not audio_url:
            raise RuntimeError(res.get('error',{}).get("message"))
        req_audio=requests.get(audio_url)
        req_audio.raise_for_status()
        if audio_url.split('?')[0].lower().endswith('.mp3'):
            with open(data['filename'], 'wb') as f:
                f.write(req_audio.content)
        else:
            with open(data['filename']+".wav", 'wb') as f:
                f.write(req_audio.content)
            tools.wav2mp3(data['filename']+".wav", data['filename'])


