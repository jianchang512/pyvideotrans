import copy
import os
import re
import sys
from typing import Union, Dict, List

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

# 线程池并发

class TTSAPI(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.copydata=copy.deepcopy(self.queue_tts)
        api_url = config.params['ttsapi_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

    def _exec(self)->None:
        self._local_mul_thread()

    def _item_task(self,data_item:Union[Dict,List,None]):
        if tools.vail_file(data_item['filename']):
            return True
        try:
            text = data_item['text'].strip()
            role=data_item['role']
            if not text:
                return True
            data = {"text": text.strip(), "language": self.language, "extra": config.params['ttsapi_extra'], "voice": role,
                    "ostype": sys.platform,
                    "rate": self.rate}

            resraw = requests.post(f"{self.api_url}", data=data, verify=False)
            res = resraw.json()
            if "code" not in res or "msg" not in res:
                self.error=f'TTS-API:{res}'
                return False
            if res['code'] != 0:
                self.error=f'TTS-API:{res["msg"]}'
                return False

            url = res['data']
            res = requests.get(url)
            if res.status_code != 200:
                self.error=f'TTS-API:{url}'
                return False
            with open(data_item['filename'], 'wb') as f:
                f.write(res.content)

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error=''
            self.has_done+=1
            return True
        except requests.ConnectionError as e:
            self.error=str(e)
            config.logger.exception(e,exc_info=True)
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e,exc_info=True)
        finally:
            if self.error:
                tools.set_process(self.error, uuid=self.uuid)
            else:
                tools.set_process(f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}', uuid=self.uuid)
        return False