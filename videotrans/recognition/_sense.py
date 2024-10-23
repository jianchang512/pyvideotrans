# stt项目识别接口
from typing import Union, List, Dict

import requests

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn

"""
            请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
            requests.post(api_url, files={"file": open(audio_file, 'rb')},data={lang:2位语言代码})

            失败时返回
            res={
                "code":1,
                "msg":"错误原因"
            }

            成功时返回
            res={
                "code":0,
                "msg":"ok",
                "data":srt格式字符串
            }
"""


class SenseVoiceAPIRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        api_url = config.params['sense_url'].strip().rstrip('/').lower()
        if not api_url:
            raise Exception('必须填写自定义api地址' if config.defaulelang == 'zh' else 'Custom api address must be filled in')
        if not api_url.startswith('http'):
            api_url = f'http://{api_url}'
        api_url=api_url if api_url.endswith('/asr') else f'{api_url}/asr'
        self.api_url = api_url

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        files = {"file": open(self.audio_file, 'rb')}
        self._signal(
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        try:
            data={"lang":self.detect_language[:2]}
            res = requests.post(f"{self.api_url}", files=files,data=data, proxies={"http": "", "https": ""}, timeout=7200)
            config.logger.info(f'SenseVoice_API:{res=}')
            res = res.json()
            if "code" not in res or res['code'] != 0:
                raise Exception(f'{res}')
            if "data" not in res or len(res['data']) < 1:
                raise Exception(f'{res=}')
            self._signal(
                text=res['data'],
                type='replace_subtitle'
            )
            return tools.get_subtitle_from_srt(res['data'], is_file=False)
        except Exception as e:
            raise
