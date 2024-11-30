import copy
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发

class AI302(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        if config.params['ai302tts_model'] == 'azure':
            self.api_url='https://api.302.ai/cognitiveservices/v1'
        elif config.params['ai302tts_model'] == 'doubao':
            self.api_url='https://api.302.ai/doubao/tts_hd'
        else:
            self.api_url='https://api.302.ai/v1/audio/speech'
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
            if config.params['ai302tts_model'] == 'azure':
                return self._azure(data=data_item)
            if config.params['ai302tts_model'] == 'doubao':
                return self._doubao(data=data_item)
            return self._openai(data=data_item)
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

    def _openai(self, data):
        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        response = requests.post('https://api.302.ai/v1/audio/speech', headers={
            'Authorization': f'Bearer {config.params["ai302tts_key"]}',
            'User-Agent': 'pyvideotrans',
            'Content-Type': 'application/json'
        }, json={
            "model": config.params['ai302tts_model'],
            "input": data['text'],
            "voice": data['role'],
            "speed": speed
        }, verify=False,proxies=self.proxies)
        if response.status_code != 200:
            self.error = f"status_code={response.status_code} {response.reason}"
            return
        with open(data['filename'], 'wb') as f:
            f.write(response.content)
        self.has_done += 1
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''

    def _azure(self, data):
        ssml = f"""<speak version='1.0' xml:lang='{self.language}'>
        <voice name='{data["role"]}' lang='{self.language}'>            
            <prosody rate="{self.rate}" pitch='{self.pitch}'  volume='{self.volume}'>
            {data["text"]}
            </prosody>
        </voice>
        </speak>"""
        # Riff48Khz16BitMonoPcm
        headers = {
            'Authorization': f'Bearer {config.params["ai302tts_key"]}',
            'X-Microsoft-OutputFormat': 'riff-48khz-16bit-mono-pcm',
            'User-Agent': 'pyvideotrans',
            'Content-Type': 'application/ssml+xml',
            'Accept': '*/*',
            'Host': 'api.302.ai',
            'Connection': 'keep-alive'
        }
        response = requests.post('https://api.302.ai/cognitiveservices/v1',
                                 headers=headers,
                                 data=ssml.encode('utf-8'),
                                 verify=False,proxies=self.proxies)
        if response.status_code != 200:
            self.error = f'status_code={response.status_code} {response.reason}'
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
                "voice_type": tools.get_302ai_doubao(role_name=data['role']),
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
            'Authorization': f'Bearer {config.params["ai302tts_key"]}',
            'User-Agent': 'pyvideotrans',
            'Content-Type': 'application/json'
        }, json=payload, verify=False,proxies=self.proxies)
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
