# zh_recogn 识别
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests,time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.configure._except import  NO_RETRY_EXCEPT
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class AI302Recogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        self._signal(text=f"start speech to srt")
        model_name = params.get('ai302_model_recogn','whisper-1')
        print(f'{model_name=}')
        if model_name=='gpt-4o-transcribe-diarize':
            # 说话人识别模型
            return self._diarize()
        if model_name.startswith('gpt-4o-'):
            # gpt-4o 只可返回json格式
            return self._thrid_api()
        
        # 转为 mp3

        apikey = params.get('ai302_key')
        langcode = self.detect_language[:2].lower()
        url = "https://api.302.ai/v1/audio/transcriptions"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {apikey}',
        }

        prompt = settings.get(f'initial_prompt_{self.detect_language}')

        logger.debug(f'{prompt=}')
        response = requests.post(url,
                                 files={"file": open(self.audio_file, 'rb')},
                                 data={
                                     "model": model_name,
                                     'response_format': 'verbose_json',
                                     'prompt': prompt,
                                     'language': langcode},
                                 headers=headers)
        if response.status_code!=200:
             raise RuntimeError(response.text)

        for i, it in enumerate(response.json()['segments']):
            if self._exit():
                return
            srt = {
                "line": i + 1,
                "start_time": int(it['start'] * 1000),
                "end_time": int(it['end'] * 1000),
                "text": it['text']
            }
            srt["endraw"] = tools.ms_to_time_string(ms=srt["end_time"])
            srt["startraw"] = tools.ms_to_time_string(ms=srt["start_time"])
            srt['time'] = f'{srt["startraw"]} --> {srt["endraw"]}'
            self._signal(
                text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
                type='subtitle'
            )
            self.raws.append(srt)
        return self.raws

    def _thrid_api(self):
        # 发送请求
        model_name = params.get('ai302_model_recogn','whisper-1')
        raws = self.cut_audio()
        apikey = params.get('ai302_key')
        langcode = self.detect_language[:2].lower()
        url = "https://api.302.ai/v1/audio/transcriptions"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {apikey}',
        }
        prompt = settings.get(f'initial_prompt_{self.detect_language}')
        logger.debug(f'{prompt=}')
        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            response = requests.post(url,
                 files={"file": open(it['file'], 'rb')},
                 data={
                     "model": model_name,
                     'response_format': 'json',
                     'prompt': prompt,
                     'language': langcode},
                headers=headers)
                
            if response.status_code!=200:
                err=response.text
                continue
            res_json=response.json()
            if "text" not in res_json or "error" in res_json:
                err=f'{res_json}'
                continue
            logger.debug(f'{res_json=}')
            raws[i]['text'] = res_json['text']
            ok_nums+=1
        if ok_nums<1:
            raise RuntimeError(err)
        return raws


    def _diarize(self):
        apikey = params.get('ai302_key')

        langcode = self.detect_language[:2].lower()
        url = "https://api.302.ai/v1/audio/transcriptions"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {apikey}',
        }

        prompt = settings.get(f'initial_prompt_{self.detect_language}')


        response = requests.post(url,
             files={"file":open(self.audio_file, 'rb')},
             data={
                 "model": 'gpt-4o-transcribe-diarize',
                 'response_format': 'diarized_json',
                 # 'prompt': prompt,
                 'language': langcode},
             headers=headers)
        # print(f'{prompt=},{headers=},{langcode=},{self.audio_file=}')
        if response.status_code!=200:
            raise RuntimeError(response.text)

        raws=[]
        speaker_list=[]
        speaker_name=[]

        for i, it in enumerate(response.json()['segments']):
            if not it.get('text','').strip():
                continue
            raws.append({
                "line": len(raws) + 1,
                "start_time": it['start'] * 1000,
                "end_time": it['end'] * 1000,
                "text": it['text'],
                "time": tools.ms_to_time_string(ms=it['start'] * 1000) + ' --> ' + tools.ms_to_time_string(
                    ms=it['end'] * 1000),
            })

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
