# zh_recogn 识别
import re
import time
from pathlib import Path
from typing import Union, List, Dict

import httpx
import requests
import json


from videotrans.configure import config


from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
from openai import OpenAI, APIConnectionError

class OpenaiAPIRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.api_url = self._get_url(config.params['openairecognapi_url'])

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        if not re.search(r'localhost', self.api_url) and not re.match(r'https?://(\d+\.){3}\d+', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro
        else:
            self.proxies = None

        try:
            # 大于20M 从wav转为mp3
            if Path(self.audio_file).stat().st_size > 20971520:
                mp3_tmp = config.TEMP_HOME + f'/recogn{time.time()}.mp3'
                tools.runffmpeg([
                    "-y",
                    "-i",
                    Path(self.audio_file).as_posix(),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    mp3_tmp
                ])
                # 如果仍大于 再转为8k
                if not Path(mp3_tmp).exists() or Path(mp3_tmp).stat().st_size > 20971520:
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        Path(self.audio_file).as_posix(),
                        "-ac",
                        "1",
                        "-ar",
                        "8000",
                        mp3_tmp
                    ])
                if Path(mp3_tmp).exists():
                    self.audio_file = mp3_tmp
            if not Path(self.audio_file).is_file():
                raise Exception(f'No file {self.audio_file}')
            # 发送请求
            raws=[]
            client=OpenAI(api_key=config.params['openairecognapi_key'], base_url=self.api_url,  http_client=httpx.Client(proxy=self.proxies))
            with open(self.audio_file, 'rb') as file:
                transcript = client.audio.transcriptions.create(
                    file=(self.audio_file, file.read()),
                    model=config.params["openairecognapi_model"],
                    prompt=config.params['openairecognapi_prompt'],
                    response_format="verbose_json"
                )
                if not hasattr(transcript, 'segments'):
                    raise Exception(f'返回字幕无时间戳，无法使用')
                for i, it in enumerate(transcript.segments):
                    raws.append({
                        "line":len(raws)+1,
                        "start_time":it['start']*1000,
                        "end_time":it['end']*1000,
                        "text":it['text'],
                        "time":tools.ms_to_time_string(ms=it['start']*1000)+' --> '+tools.ms_to_time_string(ms=it['end']*1000),
                    })
            return raws
        except json.decoder.JSONDecodeError as e:
            msg=re.sub(r'</?\w+[^>]*?>','',transcript.text,re.I|re.S)            
            raise Exception(msg)
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout, requests.exceptions.ProxyError) as e:
            api_url_msg = f' 当前Api: {self.api_url}' if self.api_url else ''
            proxy_msg = '' if not self.proxies else f'{list(self.proxies.values())[0]}'
            proxy_msg = f'' if not proxy_msg else f',当前代理:{proxy_msg}'
            msg = f'网络连接错误{api_url_msg} {proxy_msg}' if config.defaulelang == 'zh' else str(e)
            raise Exception(msg)
        except Exception:
            raise

    def _get_url(self, url=""):
        baseurl = "https://api.openai.com/v1"
        if not url:
            return baseurl
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return baseurl
        # 存在 /v1/xx的，改为 /v1
        if re.match(r'.*/v1/.*$', url):
            return re.sub(r'/v1.*$', '/v1', url)
        # 不是/v1结尾的改为 /v1
        if url.find('/v1') == -1:
            return url + "/v1"
        return url
