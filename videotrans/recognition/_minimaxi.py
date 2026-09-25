import logging,time
from dataclasses import dataclass
from pathlib import Path
from typing import List,  Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params,settings,logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem



@dataclass
class MinimaxiASR(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get('minimaxi_apikey')
        self.api_url='https://'+params.get('minimaxi_apiurl','api.minimax.cn')+'/v1/speech_to_text'
        self.model_name = params.get('minimaxi_asr_model','asr-1.0')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),  after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        self.signal(text=f"start speech to srt")
        raws = self.cut_audio()
        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            res_json=self._req(it['filename'])
            if "error" in res_json:
                err=res_json['error']['message']
                continue
            raws[i]['text'] = res_json['text']
            ok_nums+=1
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
        if ok_nums<1:
            raise SpeechToTextError(err+f'\n{self.model_name=}')
        return raws


    def _req(self,file):
        payload = {
            "model": self.model_name,
            "response_format": "json",
            "timestamp_level": "sentence",
            "stream": "false"
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with open(file, "rb") as audio_file:
                files = {
                    "file": (Path(file).name, audio_file),
                }
                response = requests.post(self.api_url, data=payload,headers=headers, files=files, verify=False)
                return response.json()
        except Exception as e:
            return {"error":{"message":str(e)}}


