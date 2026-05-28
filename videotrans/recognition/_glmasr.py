from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import requests
import time

from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import SpeechToTextError, StopTask
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem


@dataclass
class GLMASRRecogn(BaseRecogn):
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        apikey = params.get('zhipu_key')

        url = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"
        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            with open(it['filename'], "rb") as f:
                file_data = f.read()
            files = { "file":   (Path(it['filename']).name, file_data) }
            payload = {
                "model": "glm-asr-2512",
                "stream": "false"
            }
            headers = {"Authorization": f"Bearer {apikey}"}
            retry=0
            while 1:
                if retry>=settings.get('retry_nums'):
                    it['text']=''
                    break
                response = requests.post(url, data=payload, files=files, headers=headers)
                if response.status_code in [401,403,404,422]:
                    raise StopTask(response.text)
                retry+=1
                if response.status_code==200:                    
                    it['text']=response.json()['text'].strip()
                    ok_nums+=1
                    self.signal(text=f"{i+1}/{len(raws)}")
                    self.signal(
                        text=f'{it["text"]}\n',
                        type='subtitle'
                    )
                    break
                
                try:
                    err_json=response.json()
                except Exception:
                    raise SpeechToTextError(response.text)
                else:
                    logger.error(err_json)
                    code=str(err_json['error']['code'])
                    if code in ["1302","1303","1214"]:
                        time.sleep(5)
                        continue
                    raise SpeechToTextError(err_json['error']['message'])

        if ok_nums<1:
            raise SpeechToTextError(err)
        return raws