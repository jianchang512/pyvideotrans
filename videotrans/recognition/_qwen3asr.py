import base64
import json
import logging,time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import dashscope
import requests
from dashscope.common.error import AuthenticationError
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed, before_log, after_log

from videotrans.configure.excepts import SpeechToTextError, StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import params, settings, logger
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem

@dataclass
class Qwen3ASRRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        spaceid=params.get('qwenmt_spaceid', '')
        if spaceid and  not spaceid.startswith('http'):
            self.api_url = f'https://{spaceid}.cn-beijing.maas.aliyuncs.com/api/v1'
        elif spaceid and spaceid.startswith('http'):
            self.api_url = spaceid.strip().strip('/')
        self.raws = self.cut_audio()

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        api_key=params.get('qwenmt_key','')
        model=self.model_name
        if model.startswith('qwen-audio-3.0-asr-flash') or model.startswith('fun-asr-flash'):
            return self._audio_funasr_flash(api_key,model)

        error=""
        ok_nums=0
        dashscope.base_http_api_url = self.api_url
        for i, it in enumerate(self.raws):
            try:
                response = dashscope.MultiModalConversation.call(
                    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
                    api_key=api_key,
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"audio": it['filename']},
                        ]
                    }],
                    result_format="message",
                    asr_options={
                        "language": None if self.detect_language=='auto' else  self.detect_language.split('-')[0], # 可选，若已知音频的语种，可通过该参数指定待识别语种，以提升识别准确率
                        "enable_lid": True,
                        "enable_itn": True
                    }
                )
            except AuthenticationError as e:
                raise StopTask(str(e))

            if not hasattr(response, 'output') or not hasattr(response.output, 'choices') or not response.output.choices:
                error=f'{response.code}:{response.message}'
                continue
                
            ok_nums+=1
            txt=''
            for t in response.output.choices[0]['message']['content']:
                txt += t['text']
            self.raws[i]['text'] = txt
            self.signal(text=f"{txt}\n",type="subtitle")
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
            
        if ok_nums==0:
            raise SpeechToTextError(error)
        return self.raws

 
    # 针对 qwen-audio-3.0-asr-flash 和 fun-asr-flash-2026-06-15
    def _audio_funasr_flash(self,api_key,model):
        if self._exit(): return
        # 发送请求

        error=""
        ok_nums=0
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",
        }
        # /services/aigc/multimodal-generation/generation
        if self.api_url.endswith('/v1'):
            self.api_url+='/services/aigc/multimodal-generation/generation'

        for i, it in enumerate(self.raws):
            base64_str = base64.b64encode(Path(it['filename']).read_bytes()).decode()
            data_uri = f"data:audio/wav;base64,{base64_str}"

            payload = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": data_uri,
                                    },
                                }
                            ],
                        }
                    ]
                },
                "parameters": {
                    "format": "wav",
                    "sample_rate": "16000",
                },
            }


            response = requests.post(self.api_url, headers=headers, json=payload,verify=False,proxies={"https":"","http":""})
            if response.status_code in [400,401,403,404,422]:
                raise StopTask(response.text)
            if response.status_code!=200:
                error=response.text
                continue
            try:
                data=response.json()
            except json.JSONDecodeError:
                error=response.text
                continue
            if not data.get('output') or not data.get('output',{}).get('text'):
                error=response.text
                continue
            ok_nums+=1
            _text=data.get('output').get('text')
            self.signal(text=_text+"\n",type="subtitle")
            self.raws[i]['text'] = _text
            if self.asr_wait>0:
                time.sleep(self.asr_wait)

        if ok_nums==0:
            raise SpeechToTextError(error)
        return self.raws