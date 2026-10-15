import math
from dataclasses import dataclass
from typing import List, Union
import httpx
import requests
from deepgram import (
    DeepgramClient
)
from deepgram.core import ApiError
from pydub import AudioSegment

from videotrans.configure.config import tr, params, settings, logger
from videotrans.configure.excepts import SpeechToTextError
from videotrans.process._stt_utils import _resegment
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._ffmpeg_runner import runffmpeg
from videotrans.util._ffprobe import get_audio_time


@dataclass(repr=False)
class FishAudioApiRecogn(BaseRecogn):

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        runffmpeg( ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/fishaudioapi-tmp.mp3'])
        self.audio_file = self.cache_folder + '/fishaudioapi-tmp.mp3'
        audio_ms=get_audio_time(self.audio_file)
        self.signal(
            text=tr("Recognition may take a while, please be patient"))
        url = "https://api.fish.audio/v1/asr"
        text_words=[{
            "text":"",
            "words":[]
        }]
        mp3_list=[]
        if audio_ms<3600000:
            mp3_list=[self.audio_file]
        else:
            # 每1个小时为一个分片
            _chunk_ms=3600000
            _total=math.ceil(audio_ms/_chunk_ms)
            audio_data=AudioSegment.from_file(self.audio_file,format="mp3")
            for i in range(_total):
                _chunk_mp3=f'{self.cache_folder}-{i}.mp3'
                _start_ms=i*_chunk_ms
                if i==_total-1:
                    audio_data[_start_ms:].export(_chunk_mp3,format="mp3")
                else:
                    audio_data[_start_ms:_start_ms+_chunk_ms].export(_chunk_mp3,format="mp3")
                mp3_list.append({"offset":_start_ms,"filename":_chunk_mp3})
            logger.debug(f'Fish.audio渠道：当前待识别音频时长超过1个小时共 ({audio_ms/1000}s)，按每小时切分为 {_total} 片\n{mp3_list=}')

        language=self.detect_language.split('-')[0]
        headers = {
            "model": "transcribe-1-pro",
            "Authorization": f"Bearer {params.get('fishaudio_key')}"
        }
        for audio_file in mp3_list:
            files = { "audio": ("fishaudioapi-tmp.mp3", open(audio_file, "rb")) }
            payload = {
                "ignore_timestamps": False,
                "tag_audio_events":False,
                "diarize":False
            }
            if language!='auto':
                payload['language']=language


            response = requests.post(url, data=payload, files=files, headers=headers)
            if response.status_code!=200:
                logger.error(f'fish.audio出错:{response.text}')
                raise SpeechToTextError(response.json()['message'] if "message" in response.text else response.text)

            text_words[0]['words'].extend(
                [
                    {"start":it['start'],"end":it['end'],"word":it['text']} for it in response.json()['segments']
                ]
            )

        min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 200)
        # 最长片段不得大于25s,并且不得小于 _min_speech
        max_speech = min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000)
        if max_speech<=min_speech:
            max_speech=min_speech+1000
        return _resegment(text_words, language, max_speech, min_speech, logs_file=None)
