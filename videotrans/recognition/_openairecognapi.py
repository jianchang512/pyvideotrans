# zh_recogn 识别
import re
import time
from pathlib import Path
from typing import Union, List, Dict

import httpx
import requests
import json

from pydub import AudioSegment

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
        if not re.search(r'api\.openai\.com/v1', self.api_url):
            return self._thrid_api()
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
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout, requests.exceptions.ProxyError) as e:
            api_url_msg = f' 当前Api: {self.api_url}' if self.api_url else ''
            proxy_msg = '' if not self.proxies else f'{list(self.proxies.values())[0]}'
            proxy_msg = f'' if not proxy_msg else f',当前代理:{proxy_msg}'
            msg = f'网络连接错误{api_url_msg} {proxy_msg}' if config.defaulelang == 'zh' else str(e)
            raise Exception(msg)
        except Exception:
            raise

    def _thrid_api(self):
        try:
            # 发送请求
            raws=self.cut_audio()
            client=OpenAI(api_key=config.params['openairecognapi_key'], base_url=self.api_url,  http_client=httpx.Client(proxy=self.proxies,timeout=7200))
            for i,it in enumerate(raws):
                with open(it['file'], 'rb') as file:
                    transcript = client.audio.transcriptions.create(
                        file=(it['file'], file.read()),
                        model=config.params["openairecognapi_model"],
                        prompt=config.params['openairecognapi_prompt'],
                        timeout=7200,
                        response_format="json"
                    )
                    if not hasattr(transcript, 'text'):
                        continue
                    raws[i]['text']=transcript.text
            return raws
        except APIConnectionError as e:
            api_url_msg = f' 当前Api: {self.api_url}' if self.api_url else ''
            proxy_msg = '' if not self.proxies else f'{list(self.proxies.values())[0]}'
            proxy_msg = f'' if not proxy_msg else f',当前代理:{proxy_msg}'
            msg = f'网络连接错误{api_url_msg} {proxy_msg}' if config.defaulelang == 'zh' else str(e)
            raise Exception(msg)
        except Exception:
            raise
    def cut_audio(self):

        sampling_rate=16000
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import (
            VadOptions,
            get_speech_timestamps
        )

        def convert_to_milliseconds(timestamps):
            milliseconds_timestamps = []
            for timestamp in timestamps:
                milliseconds_timestamps.append(
                    {
                        "start": int(round(timestamp["start"] / sampling_rate * 1000)),
                        "end": int(round(timestamp["end"] / sampling_rate * 1000)),
                    }
                )

            return milliseconds_timestamps
        vad_p={
            "threshold":float(config.settings['threshold']),
            "min_speech_duration_ms":int(config.settings['min_speech_duration_ms']),
            "max_speech_duration_s":float(config.settings['max_speech_duration_s']) if float(config.settings['max_speech_duration_s'])>0 else float('inf'),
            "min_silence_duration_ms":int(config.settings['min_silence_duration_ms']),
            "speech_pad_ms":int(config.settings['speech_pad_ms'])
        }
        speech_chunks=get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),vad_options=VadOptions(**vad_p))
        speech_chunks=convert_to_milliseconds(speech_chunks)

        # 在config.TEMP_DIR下创建一个以当前时间戳为名的文件夹，用于保存切割后的音频片段
        dir_name = f"{config.TEMP_DIR}/{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"Saving segments to {dir_name}")
        data=[]
        audio = AudioSegment.from_file(self.audio_file,format=self.audio_file[-3:])
        for it in speech_chunks:
            start_ms, end_ms=it['start'],it['end']
            chunk = audio[start_ms:end_ms]
            file_name=f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({
                "start_time":start_ms,
                "end_time":end_ms,
                "file":file_name,
                "text":"",
                "time":tools.ms_to_time_string(ms=start_ms)+' --> '+tools.ms_to_time_string(ms=end_ms)
            })

        return data

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
