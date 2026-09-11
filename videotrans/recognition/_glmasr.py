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
            # 限流(1302/1303/1214)时等待后重试，至少重试 3 次；其他错误直接报错
            rate_limited=0
            max_rate_limited=max(int(settings.get('retry_nums', 1) or 1), 3)
            while 1:
                response = requests.post(url, data=payload, files=files, headers=headers, timeout=(30, 300))
                if response.status_code in [401,403,404,422]:
                    raise StopTask(response.text)
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
                logger.error(err_json)
                _error=(err_json.get('error') if isinstance(err_json, dict) else None) or {}
                code=str(_error.get('code', ''))
                err=_error.get('message') or response.text
                if code in ["1302","1303","1214"]:
                    if rate_limited < max_rate_limited:
                        rate_limited+=1
                        time.sleep(5 * rate_limited)
                        continue
                    it['text']=''
                    break
                raise SpeechToTextError(err)
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
        if ok_nums<1:
            raise SpeechToTextError(err)
        return raws