import logging,time
from dataclasses import dataclass
from typing import List,  Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params,settings,logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem



@dataclass
class OpenRouterASR(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get('openrouter_key')
        self.model_name = params.get('openrouter_asr_model')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),  after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        self.signal(text=f"start speech to srt")
        raws = self.cut_audio()
        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            res_json=self._req(it['filename'])
            print(f'{res_json=}')
            if "error" in res_json:
                err=res_json['error']['message']
                continue
            raws[i]['text'] = res_json['text']
            ok_nums+=1
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
        if ok_nums<1:
            raise SpeechToTextError(err)
        return raws


    def _req(self,file):
        url = "https://openrouter.ai/api/v1/audio/transcriptions"
        payload = {
            "input_audio": {
                "data": self._audio_to_base64(file),
                "format": "wav"
            },
            "model": self.model_name
        }
        if self.detect_language and self.detect_language!='auto':
            payload["language"]=self.detect_language.split('-')[0]
        headers = {"Authorization": f"Bearer {self.api_key}","Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers,verify=False)
            return response.json()
        except Exception as e:
            return {"error":{"message":str(e)}}


