# zh_recogn 识别
from typing import Union, List, Dict

import requests

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

"""
            请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
            requests.post(api_url, files={"audio": open(audio_file, 'rb')})

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
        files = {"audio": open(self.audio_file, 'rb')}
        self._signal(text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        try:
            res = requests.post(f"{self.api_url}", files=files, proxies={"http": "", "https": ""}, timeout=3600)
            config.logger.info(f'RECOGN_API:{res=}')
            res = res.json()
            if "code" not in res or res['code'] != 0:
                raise Exception(f'{res["msg"]}')
            if "data" not in res or len(res['data']) < 1:
                raise Exception(f'识别出错{res=}')
            return res['data']
        except Exception as e:
            raise
