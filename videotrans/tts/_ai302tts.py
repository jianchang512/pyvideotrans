import copy
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans import tts
from videotrans.util import tools


# 线程池并发

class AI302(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.proxies=None
        
    def _exec(self):
        self.dub_nums=1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            if data_item['role'] not in tts.DOUBAO_302AI:
                return self._azure(data=data_item)
            data_item['role']=tts.DOUBAO_302AI[data_item['role']]
            return self._doubao(data=data_item)
        except requests.exceptions.ProxyError:
            self.error='连接代理出错，请检查' if config.defaulelang=='zh' else 'Connect to proxy failed, please check'
        except (requests.ConnectionError,requests.Timeout,requests.exceptions.RetryError) as e:
            # 中文和英文
            self.error = '连接302.ai失败，请尝试使用或切换代理' if config.defaulelang=='zh' else 'Connect to 302.ai failed, please try to use or switch proxy'
        except Exception as e:
            self.error = str(e)
        finally:
            if self.error:
                self._signal(text=f'{self.error}')
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')


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
                                 verify=False,proxies=None)
        if response.status_code == 400:
            self.error=f'该角色 {data["role"]} 可能不支持，请使用其他角色'
            raise 
        if response.status_code != 200:
            config.logger.info(f'302.ai azure:{headers=},{ssml=},{response=}')
            self.error = f'status_code={response.status_code} {response.text=}'
            return
        # wav 需转为mp3
        with open(data['filename'] + ".wav", 'wb') as f:
            f.write(response.content)
        self.has_done += 1
        tools.wav2mp3(data['filename'] + ".wav", data['filename'])
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''
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
        }, json=payload, verify=False,proxies=None)
        if response.status_code != 200:
            self.error = f'status_code={response.status_code} {response.reason}'
            return
        res = response.json()
        if res['code'] != 3000:
            self.error = f"{res['code']}:{res['message']}"
        else:
            self._base64_to_audio(res['data'], data['filename'])
        self.has_done += 1
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
