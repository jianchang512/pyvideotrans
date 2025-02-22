# zh_recogn 识别
import re
import time
from typing import Union, List, Dict

import requests

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn

"""
            请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
            requests.post(api_url, files={"audio": open(audio_file, 'rb')},data={"language":2位语言代码})

            失败时返回
            res={
                "code":1,
                "msg":"错误原因"
            }

            成功时返回
            res={
                "code":0,
                "data":[
                    {
                        "text":"字幕文字",
                        "time":'00:00:01,000 --> 00:00:06,500'
                    },
                    {
                        "text":"字幕文字",
                        "time":'00:00:06,900 --> 00:00:12,200'
                    },
                ]
            }
"""


class APIRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        api_url = config.params['recognapi_url'].strip().rstrip('/').lower()
        if not api_url:
            raise Exception('必须填写自定义api地址' if config.defaulelang == 'zh' else 'Custom api address must be filled in')
        if not api_url.startswith('http'):
            api_url = f'http://{api_url}'
        if config.params['recognapi_key']:
            if api_url.find('?') > 0:
                api_url += f'&sk={config.params["recognapi_key"]}'
            else:
                api_url += f'?sk={config.params["recognapi_key"]}'
        self.api_url = api_url

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if re.search(r'api\.gladia\.io',self.api_url,re.I):
            return self._whisperzero()
        with open(self.audio_file, 'rb') as f:
            chunk=f.read()    
        files = {"audio": chunk}
        self._signal(
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        try:
            res = requests.post(f"{self.api_url}",data={"language":self.detect_language}, files=files, proxies={"http": "", "https": ""}, timeout=3600)
            res = res.json()
            if "code" not in res or res['code'] != 0:
                raise Exception(f'{res["msg"]}')
            if "data" not in res or len(res['data']) < 1:
                raise Exception(f'识别出错{res=}')
            self._signal(
                text=tools.get_srt_from_list(res['data']),
                type='replace_subtitle'
            )
            return res['data']
        except Exception as e:
            raise

    def _whisperzero(self):
        api_key=config.params.get("recognapi_key")
        if not api_key:
            raise Exception('必须填写api key' if config.defaulelang=='zh' else 'api key must be filled in')
        # 上传 self.audio_file
        with open(self.audio_file, "rb") as f:
            audio_file=f.read()
        files = {
            "audio": (self.audio_file, audio_file, "audio/wav")  # Content-Type 音频类型，有些API需要特别指定
        }

        response = requests.post("https://api.gladia.io/v2/upload", files=files, headers= {
            "x-gladia-key": api_key
        })
        response.raise_for_status()
        audio_url=response.json()['audio_url']

        # 开始转录


        payload = {
            "detect_language": True if not self.detect_language or self.detect_language=='auto' else False,
            "enable_code_switching": False,
            "language": "" if not self.detect_language or self.detect_language=='auto' else self.detect_language[:2],
            "subtitles": True,
            "subtitles_config": {
                "formats": ["srt"],
                "minimum_duration": 1,
                "maximum_duration": 15.5,
                "maximum_characters_per_row": 80,
                "maximum_rows_per_caption": 2,
                "style": "default"
            },
            "sentences": True,
            "punctuation_enhanced": True,
            "audio_url": audio_url
        }


        response = requests.request("POST", 'https://api.gladia.io/v2/pre-recorded', json=payload, headers={
            "x-gladia-key": api_key,
            "Content-Type": "application/json"
        })
        response.raise_for_status()
        id=response.json()['id']

        # 获取结果
        while 1:
            time.sleep(5)
            response = requests.get(f"https://api.gladia.io/v2/pre-recorded/{id}", headers={"x-gladia-key": api_key})
            response.raise_for_status()
            d=response.json()
            if d['status']=='error':
                config.logger.error(d)
                raise Exception(f"Error:{d['error_code']}")
            if d['status']=='done':
                config.logger.info(d)
                sens=d['result']['transcription']['subtitles'][0]['subtitles']
                raws=tools.get_subtitle_from_srt(sens,is_file=False)
                if self.detect_language and self.detect_language[:2] in ['zh','ja','ko']:
                    for i,it in enumerate(raws):
                        text=re.sub(r'\s+','',it['text'])
                        raws[i]['text']=text
                return raws


