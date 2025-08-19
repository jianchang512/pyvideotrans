# zh_recogn 识别
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Union

import requests

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

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
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
import logging

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class APIRecogn(BaseRecogn):
    raws: List = field(default_factory=list, init=False)

    def __post_init__(self):
        super().__post_init__()
        self.raws = []
        api_url = config.params['recognapi_url'].strip().rstrip('/').lower()
        if not api_url:
            raise RuntimeError('必须填写自定义api地址' if config.defaulelang == 'zh' else 'Custom api address must be filled in')

        if not api_url.startswith('http'):
            api_url = f'http://{api_url}'

        if config.params.get('recognapi_key'):
            if '?' in api_url:
                api_url += f'&sk={config.params["recognapi_key"]}'
            else:
                api_url += f'?sk={config.params["recognapi_key"]}'

        self.api_url = api_url

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if re.search(r'api\.gladia\.io', self.api_url, re.I):
            return self._whisperzero()
        with open(self.audio_file, 'rb') as f:
            chunk = f.read()
        files = {"audio": chunk}
        self._signal(
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')

        res = requests.post(f"{self.api_url}", data={"language": self.detect_language}, files=files,
                            proxies={"http": "", "https": ""}, timeout=3600)
        res.raise_for_status()
        res = res.json()
        if "code" not in res or res['code'] != 0:
            raise RuntimeError(f'{res["msg"]}')
        if "data" not in res or len(res['data']) < 1:
            raise RuntimeError(f'识别出错{res=}')
        self._signal(
            text=tools.get_srt_from_list(res['data']),
            type='replace_subtitle'
        )
        return res['data']

    def _whisperzero(self):
        api_key = config.params.get("recognapi_key")
        if not api_key:
            raise RuntimeError('必须填写api key' if config.defaulelang == 'zh' else 'api key must be filled in')
        # 上传 self.audio_file
        with open(self.audio_file, "rb") as f:
            audio_file = f.read()
        files = {
            "audio": (self.audio_file, audio_file, "audio/wav")  # Content-Type 音频类型，有些API需要特别指定
        }

        response = requests.post("https://api.gladia.io/v2/upload", files=files, headers={
            "x-gladia-key": api_key
        })
        response.raise_for_status()
        audio_url = response.json()['audio_url']

        payload = {
            "detect_language": True if not self.detect_language or self.detect_language == 'auto' else False,
            "enable_code_switching": False,
            "language": "" if not self.detect_language or self.detect_language == 'auto' else self.detect_language[:2],
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
        id = response.json()['id']

        # 获取结果
        while 1:
            time.sleep(5)
            response = requests.get(f"https://api.gladia.io/v2/pre-recorded/{id}", headers={"x-gladia-key": api_key})
            response.raise_for_status()
            d = response.json()
            if d['status'] == 'error':
                config.logger.error(d)
                raise RuntimeError(f"Error:{d['error_code']}")
            if d['status'] == 'done':
                config.logger.info(d)
                sens = d['result']['transcription']['subtitles'][0]['subtitles']
                raws = tools.get_subtitle_from_srt(sens, is_file=False)
                if self.detect_language and self.detect_language[:2] in ['zh', 'ja', 'ko']:
                    for i, it in enumerate(raws):
                        text = re.sub(r'\s+', '', it['text'])
                        raws[i]['text'] = text
                return raws
