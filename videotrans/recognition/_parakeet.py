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

class ParaketRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.api_url = config.params['parakeet_address']

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        self.proxies = None
        try:

            # 发送请求
            raws=[]
            client=OpenAI(api_key='123456', base_url=self.api_url)
            transcript=""
            with open(self.audio_file, 'rb') as file:
                transcript = client.audio.transcriptions.create(
                    file=(self.audio_file, file.read()),
                    model='parakeet_srt_words',
                    prompt='',
                    response_format="srt"
                )
                if not transcript or  not isinstance(transcript, str):
                    raise Exception(f'返回字幕无时间戳，无法使用')
            tmp=transcript.split("----..----")
            if len(tmp)==1 or not config.settings['rephrase']:    
                raws=tools.get_subtitle_from_srt(tmp[0],is_file=False)
            else:
                try:
                    ## transcript='src字符串----..----[{'start': 2.34, 'end': 3.04, 'word': ' there'},...]'
                    words_list=json.loads(tmp[-1].strip())
                    raws=self.re_segment_sentences(words_list)
                except Exception:
                    config.logger.info(f'重新断句失败')
                    raws=tools.get_subtitle_from_srt(tmp[0],is_file=False)
                
            return raws
        except APIConnectionError as e:
            msg = f'网络连接错误 {e}' if config.defaulelang == 'zh' else str(e)
            raise Exception(msg)
        except Exception:
            raise


