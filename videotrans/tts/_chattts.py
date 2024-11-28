import copy
import json
import re
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发 返回wav数据，转为mp3

class ChatTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['chattts_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '').replace('/tts', '')
        self.proxies={"http": "", "https": ""}
        
    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            data = {"text": data_item['text'].strip(), "voice": data_item['role'], 'prompt': '', 'is_split': 1}
            res = requests.post(f"{self.api_url}/tts", data=data, proxies=self.proxies, timeout=3600)
            if res.status_code != 200:
                self.error = f'ChatTTS:{res.status_code} {res.reason}'
                return
            config.logger.info(f'chatTTS:{data=}')
            res = res.json()
            if res is None:
                self.error = 'ChatTTS端出错，请查看其控制台终端'
                return

            if "code" not in res or res['code'] != 0:
                if "msg" in res:
                    Path(data_item['filename']).unlink(missing_ok=True)
                    return
                self.error = f'{res}'
                return

            if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                tools.wav2mp3(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
                return
            resb = requests.get(res['url'])
            if resb.status_code != 200:
                self.error = (f'chatTTS:{res["url"]=}')
                return

            config.logger.info(f'ChatTTS:resb={resb.status_code=}')
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resb.content)
            time.sleep(1)
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self.error = ''

        except (requests.ConnectionError, requests.Timeout) as e:
            self.error="连接失败，请检查是否启动了api服务" if config.defaulelang=='zh' else  'Connection failed, please check if the api service is started'
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
