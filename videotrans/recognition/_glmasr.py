# zh_recogn 识别
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests,time
from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class GLMASRRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()


    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        apikey = config.params.get('zhipu_key')

        url = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"
        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            files = { "file": (Path(it['file']).name, open(it['file'], "rb")) }
            payload = {
                "model": "glm-asr-2512",
                "stream": "false"
            }
            headers = {"Authorization": f"Bearer {apikey}"}
            retry=0
            while 1:
                if retry>=RETRY_NUMS:
                    it['text']=''
                    break
                response = requests.post(url, data=payload, files=files, headers=headers)
                retry+=1
                if response.status_code==200:                    
                    it['text']=response.json()['text'].strip()
                    ok_nums+=1
                    self._signal(text=f"{i+1}/{len(raws)}")
                    self._signal(
                        text=f'{it["text"]}\n',
                        type='subtitle'
                    )
                    break
                
                try:
                    err_json=response.json()
                except:
                    raise RuntimeError(response.text)
                else:
                    config.logger.error(err_json)
                    code=str(err_json['error']['code'])
                    if code in ["1302","1303","1214"]:
                        time.sleep(5)
                        continue
                    raise RuntimeError(err_json['error']['message'])                    

        if ok_nums<1:
            raise RuntimeError(err)
        return raws