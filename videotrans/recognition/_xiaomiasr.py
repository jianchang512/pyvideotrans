# zh_recogn 识别
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List,  Union

import httpx
from openai import OpenAI, LengthFinishReasonError,NotFoundError, AuthenticationError, PermissionDeniedError,BadRequestError,APIConnectionError,APIError
from videotrans.configure.config import params,  logger, tr
from videotrans.configure import config
from videotrans.configure.excepts import SpeechToTextError, StopTask
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools
import base64
import urllib.request


@dataclass
class XiaomiASRRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'https://api.xiaomimimo.com/v1'


    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        err,ok=0,0
        err_msg=''
        for i, it in enumerate(raws):
            try:
                client = OpenAI(
                    api_key=params.get('xiaomi_key', ''),
                    base_url=self.api_url
                )
                with open(it['filename'], "rb") as f:
                    audio_bytes = f.read()
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                completion = client.chat.completions.create(
                    model="mimo-v2.5-asr",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": f"data:audio/wav;base64,{audio_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    extra_body={
                        "asr_options": {
                            "language": "auto"
                        }
                    }
                )
                
                raws[i]['text'] = completion.choices[0].message.content
                ok+=1
                self.signal(text=f'{i+1}/{len(raws)}')
            except APIConnectionError as e:
                raise StopTask(f'{tr("Unable to connect to API",self.api_url)}\n{e.message}') from e
            except (NotFoundError,AuthenticationError,PermissionDeniedError,BadRequestError) as e:
                raise StopTask((e.body.get('message') if e.body else e.message)+f'\n{self.api_url}') from e
            except APIError as e: 
                if re.search(r"insufficient.*?balance",e.message,flags=re.I):
                    raise StopTask(tr('The server returned an error message: Insufficient balance','Xiaomi ASR',self.api_url))
                err+=1
                err_msg=e
                logger.exception(e,exc_info=True)
            except Exception as e:
                err+=1
                err_msg=e
                logger.exception(e,exc_info=True)
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
            
        if ok==0:
            raise SpeechToTextError(f'Xiaomi ASR error {err_msg}')

        msg="ASR ended"
        if err > 0 and ok>0:
            msg=f'[{err}] errors, {ok} succeed'

        self.signal(text=msg)
        
        return raws

