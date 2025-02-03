# zh_recogn 识别
import os
import time
from typing import Union, List, Dict

import requests

from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
import mimetypes


class AI302Recogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        apikey = config.params.get('ai302_key')


        # 转为 mp3
        tools.runffmpeg(['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/ai302tmp.mp3'])
        self.audio_file = self.cache_folder + '/ai302tmp.mp3'
        self._signal(text=f"start speech to srt")
        langcode = self.detect_language[:2].lower()
        url = "https://api.302.ai/v1/audio/transcriptions"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {apikey}',
        }
        try:
            prompt=config.settings.get(f'initial_prompt_{self.detect_language}')
            
            config.logger.info(f'{prompt=}')
            response = requests.post(url,
                                     files={"file":open(self.audio_file, 'rb')},
                                     data={
                                         "model":'whisper-3',
                                         'response_format':'verbose_json',
                                         'prompt':prompt,
                                         'language':langcode},
                                     headers=headers)
            response.raise_for_status()
            config.logger.info(f'{response.json()=}')
            for i, it in enumerate(response.json()['segments']):
                if self._exit():
                    return
                srt = {
                    "line": i + 1,
                    "start_time": int(it['start']*1000),
                    "end_time": int(it['end']*1000),
                    "text": it['text']
                }
                srt["endraw"]= tools.ms_to_time_string(ms=srt["end_time"])
                srt["startraw"]= tools.ms_to_time_string(ms=srt["start_time"])
                srt['time'] = f'{srt["startraw"]} --> {srt["endraw"]}'
                self._signal(
                    text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
                    type='subtitle'
                )
                self.raws.append(srt)
            return self.raws
        except requests.exceptions.RequestException as e:
               raise Exception(f'为原始视频生成字幕阶段网络请求出错:{e}')
        except Exception as e:
            raise
