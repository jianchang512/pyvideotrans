# zh_recogn 识别
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Union

import httpx
from openai import OpenAI
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class OpenaiAPIRecogn(BaseRecogn):
    raws: List[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        super().__post_init__()
        self.api_url = self._get_url(config.params['openairecognapi_url'])
        if not re.search(r'localhost', self.api_url) and not re.match(r'https?://(\d+\.){3}\d+', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro
        else:
            self.proxies = None

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if not re.search(r'api\.openai\.com/v1', self.api_url) or config.params["openairecognapi_model"].find(
                'gpt-4o-') > -1:
            return self._thrid_api()

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
            raise RuntimeError(f'No {self.audio_file}')
        # 发送请求
        raws = []
        client = OpenAI(api_key=config.params['openairecognapi_key'], base_url=self.api_url,
                        http_client=httpx.Client(proxy=self.proxies))
        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model=config.params["openairecognapi_model"],
                prompt=config.params['openairecognapi_prompt'],
                language=self.detect_language[:2].lower(),
                response_format="verbose_json"
            )
            if not hasattr(transcript, 'segments'):
                raise RuntimeError(f'返回字幕无时间戳，无法使用')
            for i, it in enumerate(transcript.segments):
                raws.append({
                    "line": len(raws) + 1,
                    "start_time": it['start'] * 1000,
                    "end_time": it['end'] * 1000,
                    "text": it['text'],
                    "time": tools.ms_to_time_string(ms=it['start'] * 1000) + ' --> ' + tools.ms_to_time_string(
                        ms=it['end'] * 1000),
                })
        return raws

    def _thrid_api(self):
        # 发送请求
        raws = self.cut_audio()
        client = OpenAI(api_key=config.params['openairecognapi_key'], base_url=self.api_url,
                        http_client=httpx.Client(proxy=self.proxies, timeout=7200))
        for i, it in enumerate(raws):
            with open(it['file'], 'rb') as file:
                transcript = client.audio.transcriptions.create(
                    file=(it['file'], file.read()),
                    model=config.params["openairecognapi_model"],
                    prompt=config.params['openairecognapi_prompt'],
                    timeout=7200,
                    language=self.detect_language[:2].lower(),
                    response_format="json"
                )
                if not hasattr(transcript, 'text'):
                    continue
                raws[i]['text'] = transcript.text
        return raws

    def cut_audio(self):

        sampling_rate = 16000
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

        vad_p = {
            "threshold": float(config.settings['threshold']),
            "min_speech_duration_ms": int(config.settings['min_speech_duration_ms']),
            "max_speech_duration_s": float(config.settings['max_speech_duration_s']) if float(
                config.settings['max_speech_duration_s']) > 0 else float('inf'),
            "min_silence_duration_ms": int(config.settings['min_silence_duration_ms']),
            "speech_pad_ms": int(config.settings['speech_pad_ms'])
        }
        speech_chunks = get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),
                                              vad_options=VadOptions(**vad_p))
        speech_chunks = convert_to_milliseconds(speech_chunks)

        # 在config.TEMP_DIR下创建一个以当前时间戳为名的文件夹，用于保存切割后的音频片段
        dir_name = f"{config.TEMP_DIR}/{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)

        data = []
        audio = AudioSegment.from_file(self.audio_file, format=self.audio_file[-3:])
        for it in speech_chunks:
            start_ms, end_ms = it['start'], it['end']
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({
                "start_time": start_ms,
                "end_time": end_ms,
                "file": file_name,
                "text": "",
                "time": tools.ms_to_time_string(ms=start_ms) + ' --> ' + tools.ms_to_time_string(ms=end_ms)
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
