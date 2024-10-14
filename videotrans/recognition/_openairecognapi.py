# zh_recogn 识别
import re
import time
from pathlib import Path
from typing import Union, List, Dict


import requests
import json


from videotrans.configure import config


from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


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
                self.proxies = {"http": pro, "https": pro}
        else:
            self.proxies = {"http": "", "https": ""}

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
            transcript = requests.post(self.api_url+f'/audio/translations',verify=False, headers= {
                "Authorization": f"Bearer {config.params['openairecognapi_key']}",
                "Content-Type": "multipart/form-data"
            }, files={
                "file": open(self.audio_file, 'rb')
            }, data={
                "model": "whisper-1",
                "timestamp_granularities[]": "segment",
                "response_format": "verbose_json"
            },proxies=self.proxies)
            config.logger.info(f'{transcript.text=}')
            resdata=transcript.json()

            if 'error' in resdata and resdata['error']:
                raise Exception(resdata['error']['message'])
            if  "segments" not in resdata:
                raise Exception( f'{resdata}' if  self.api_url.startswith("https://api.openai.com") else f'该api不支持返回带时间戳字幕格式 {self.api_url} ')

            segments=resdata['segments']

            if len(segments) < 1:
                msg = '未返回识别结果，请检查文件是否包含清晰人声' if config.defaulelang == 'zh' else 'No result returned, please check if the file contains clear vocals.'
                raise Exception(msg)
            for it in segments:
                if self._exit():
                    return
                srt_tmp = {
                    "line": len(self.raws) + 1,
                    "start_time": int(it["start"] * 1000),
                    "end_time": int(it["end"] * 1000),
                    "text": it["text"]
                }
                srt_tmp["startraw"]=tools.ms_to_time_string(ms=srt_tmp["start_time"])
                srt_tmp["endraw"]=tools.ms_to_time_string(ms=srt_tmp["end_time"])
                srt_tmp['time'] = f'{srt_tmp["startraw"]} --> {srt_tmp["endraw"]}'
                self._signal(
                    text=f'{srt_tmp["line"]}\n{srt_tmp["time"]}\n{srt_tmp["text"]}\n\n',
                    type='subtitle'
                )
                self.raws.append(srt_tmp)
            return self.raws
        except json.decoder.JSONDecodeError as e:
            msg=re.sub(r'</?\w+[^>]*?>','',transcript.text,re.I|re.S)            
            raise Exception(msg)
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout, requests.exceptions.ProxyError) as e:
            api_url_msg = f',请检查Api地址,当前Api: {self.api_url}' if self.api_url else ''
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
