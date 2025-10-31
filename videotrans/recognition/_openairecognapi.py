# zh_recogn 识别
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import httpx
from openai import OpenAI
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class OpenaiAPIRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = self._get_url(config.params.get('openairecognapi_url',''))
        self._add_internal_host_noproxy(self.api_url)

    #@retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
    #       wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
    #       after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        model_name=config.params.get("openairecognapi_model",'')
        # 如果是 gpt-4o-transcribe-diarize 说话人识别默认
        if model_name.lower()=='gpt-4o-transcribe-diarize':
            return self._diarize()
        # 如果是第三方或 gpt-4o-模型
        if not re.search(r'api\.openai\.com/v1', self.api_url) or model_name.find(
                'gpt-4o-') > -1:
            return self._thrid_api()

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


        self.audio_file = mp3_tmp
        if not Path(self.audio_file).is_file():
            raise StopRetry(f'No {self.audio_file}')
        # 发送请求
        raws = []
        client = OpenAI(api_key=config.params.get('openairecognapi_key',''), base_url=self.api_url,
                        http_client=httpx.Client(proxy=self.proxy_str))
        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model=model_name,
                prompt=config.params.get('openairecognapi_prompt',''),
                language=self.detect_language[:2].lower(),
                response_format="verbose_json",
                chunking_strategy='auto',
                timestamp_granularities=["segment"]
            )
            if not hasattr(transcript, 'segments'):
                raise StopRetry(f'返回字幕无时间戳，无法使用')
            for i, it in enumerate(transcript.segments):
                raws.append({
                    "line": len(raws) + 1,
                    "start_time": it.start * 1000,
                    "end_time": it.end * 1000,
                    "text": it.text,
                    "time": tools.ms_to_time_string(ms=it.start * 1000) + ' --> ' + tools.ms_to_time_string(
                        ms=it.end * 1000),
                })
        return raws

    def _thrid_api(self):
        # 发送请求
        raws = self.cut_audio()
        client = OpenAI(
            api_key=config.params.get('openairecognapi_key',''),
            base_url=self.api_url,
            http_client=httpx.Client(proxy=self.proxy_str or None)
        )
        for i, it in enumerate(raws):
            with open(it['file'], 'rb') as file:
                transcript = client.audio.transcriptions.create(
                    file=(it['file'], file.read()),
                    model=config.params.get("openairecognapi_model",'whisper-1'),
                    prompt=config.params.get('openairecognapi_prompt',''),
                    # timeout=7200,
                    language=self.detect_language[:2].lower(),
                    response_format="json"
                )
                if not hasattr(transcript, 'text') or not transcript.text or transcript.text.strip():
                    continue
                raws[i]['text'] = transcript.text
        return raws

    def _diarize(self):

        client = OpenAI(
            api_key=config.params.get('openairecognapi_key',''),
            base_url=self.api_url,
            http_client=httpx.Client(proxy=self.proxy_str or None)
        )
        raws=[]
        speaker_list=[]
        speaker_name=[]
        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model='gpt-4o-transcribe-diarize',
                prompt=config.params.get('openairecognapi_prompt',''),
                # timeout=7200,
                language=self.detect_language[:2].lower(),
                response_format="json"
            )

            if not hasattr(transcript, 'segments') or not transcript.segments:
                raise RuntimeError('No support gpt-4o-transcribe-diarize')
            for it in transcript.segments:
                raws.append({
                    "line": len(raws) + 1,
                    "start_time": it.start * 1000,
                    "end_time": it.end * 1000,
                    "text": it.text,
                    "time": tools.ms_to_time_string(ms=it.start * 1000) + ' --> ' + tools.ms_to_time_string(
                        ms=it.end * 1000),
                })
                if not config.params.get('paraformer_spk', False):
                    continue
                sp=it.get('speaker')
                if not sp:
                    speaker_list.append(f'spk{len(speaker_list)}')
                elif sp in speaker_name:
                    speaker_list.append(f'spk{speaker_name.index(sp)}')
                else:
                    speaker_list.append(f'spk{len(speaker_list)}')
                    speaker_name.append(sp)

        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        return raws



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
