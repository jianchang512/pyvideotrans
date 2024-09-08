import copy
import os
import re
import threading
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

# 线程池并发 返回wav数据，转为mp3

class CloneVoice(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.copydata=copy.deepcopy(self.queue_tts)
        api_url = config.params['clone_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self,data_item:dict=None):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            text = data_item['text'].strip()
            if text[-1] not in self.splits:
                text += '.'
            data = {"text": text, "language": self.language}
            role=data_item['role']
            if role != 'clone':
                # 不是克隆，使用已有声音
                data['voice'] = role
                files = None
            else:
                # 克隆声音
                files = {"audio": open(data_item['filename'], 'rb')}
            res = requests.post(f"{self.api_url}/apitts", data=data, files=files, proxies={"http": "", "https": ""}, timeout=3600)

            config.logger.info(f'clone-voice:{data=},{res.text=}')
            res = res.json()
            if "code" not in res or res['code'] != 0:
                if "msg" in res and res['msg'].find("non-empty") > 0:
                    Path(data_item['filename']).unlink(missing_ok=True)
                    return
                self.error=f'{res}'
                return

            if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                tools.wav2mp3(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
                return

            resb = requests.get(res['url'])
            if resb.status_code != 200:
                self.error=f'clonevoice:{res["url"]=}'
                return
            config.logger.info(f'clone-voice:resb={resb.status_code=}')

            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resb.content)
            time.sleep(1)
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            Path(data_item['filename'] + ".wav").unlink(missing_ok=True)
            if self.inst and self.inst.precent<80:
                self.inst.precent+=0.1
            self.error=''
            self.has_done+=1
        except requests.ConnectionError as e:
            self.error=str(e)
            config.logger.exception(e,exc_info=True)
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e,exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

