# zh_recogn 识别
import os
import re
import time
from pathlib import Path
from typing import Union, List, Dict

import httpx
from openai import OpenAI

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


class OpenaiAPIRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.maxlen = 30
        self.model = None
        self.info = None

    def _exec(self) ->Union[List[Dict],None]:
        if self._exit():
            return
        self.api_url = self._get_url(config.params['openairecognapi_url'])
        if not re.search(r'localhost', self.api_url) and not re.match(r'https?://(\d+\.){3}\d+', self.api_url):
            pro=self._set_proxy(type='set')
            if pro:
                self.proxies={"http://":pro,"https://":pro}
        else:
            self.proxies={"http://":"","https://":""}

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

            client = OpenAI(api_key=config.params['openairecognapi_key'], base_url=self.api_url, http_client=httpx.Client(proxies=self.proxies))
            transcript = client.audio.transcriptions.create(
                file=open(self.audio_file, 'rb'),
                language=self.detect_language,
                model=config.params['openairecognapi_model'],
                prompt=config.params['openairecognapi_prompt'],
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
            if len(transcript.segments) < 1:
                raise Exception(
                    '未返回识别结果，请检查文件是否包含清晰人声' if config.defaulelang == 'zh' else 'No result returned, please check if the file contains clear vocals.')
            for it in transcript.segments:
                srt_tmp = {
                    "line": len(self.raws) + 1,
                    "start_time": int(it["start"] * 1000),
                    "end_time": int(it["end"] * 1000),
                    "text": it["text"]
                }
                srt_tmp['time'] = f'{tools.ms_to_time_string(ms=srt_tmp["start_time"])} --> {tools.ms_to_time_string(ms=srt_tmp["end_time"])}'
                self.raws.append(srt_tmp)
            return self.raws
        except ConnectionError as e:
            msg = f'网络连接错误，请检查代理、api地址等:{str(e)}' if config.defaulelang == 'zh' else str(e)
            raise Exception(f'{msg}')
        except Exception as e:
            raise

    def _get_url(self,url=""):
        baseurl="https://api.openai.com/v1"
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

"""
def recogn(*,
           audio_file=None,
           cache_folder=None,
           detect_language=None,
           uuid=None,
           set_p=None,
           inst=None):
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    api_url = get_url(config.params['openairecognapi_url'])
    if not re.search(r'localhost', api_url) and not re.match(r'https?://(\d+\.){3}\d+', api_url):
        update_proxy(type='set')
    if not api_url.startswith('http'):
        api_url = f'http://{api_url}'

    tools.set_process(
            f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient',
            type='logs',
            uuid=uuid)
    try:
        # 大于20M 从wav转为mp3
        if Path(audio_file).stat().st_size > 20971520:
            mp3_tmp = config.TEMP_HOME + f'/recogn{time.time()}.mp3'
            tools.runffmpeg([
                "-y",
                "-i",
                Path(audio_file).as_posix(),
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
                    Path(audio_file).as_posix(),
                    "-ac",
                    "1",
                    "-ar",
                    "8000",
                    mp3_tmp
                ])
            audio_file = mp3_tmp

        client = OpenAI(api_key=config.params['openairecognapi_key'], base_url=api_url, http_client=httpx.Client())
        transcript = client.audio.transcriptions.create(
            file=open(audio_file, 'rb'),
            language=detect_language,
            model=config.params['openairecognapi_model'],
            prompt=config.params['openairecognapi_prompt'],
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
        if len(transcript.segments) < 1:
            raise Exception(
                '未返回识别结果，请检查文件是否包含清晰人声' if config.defaulelang == 'zh' else 'No result returned, please check if the file contains clear vocals.')
        raw_srts = []
        for it in transcript.segments:
            srt_tmp = {
                "line": len(raw_srts) + 1,
                "start_time": int(it["start"] * 1000),
                "end_time": int(it["end"] * 1000),
                "text": it["text"]
            }
            srt_tmp[
                'time'] = f'{tools.ms_to_time_string(ms=srt_tmp["start_time"])} --> {tools.ms_to_time_string(ms=srt_tmp["end_time"])}'
            raw_srts.append(srt_tmp)
    except ConnectionError as e:
        msg = f'网络连接错误，请检查代理、api地址等:{str(e)}' if config.defaulelang == 'zh' else str(e)
        raise Exception(f'{msg}')
    except Exception as e:
        raise
    else:
        return raw_srts
    finally:
        if shound_del:
            update_proxy(type='del')

"""