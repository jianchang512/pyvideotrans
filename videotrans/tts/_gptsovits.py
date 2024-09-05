import copy
import os
import sys
import threading
import time
from pathlib import Path
from typing import Union, Dict, List

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

# 线程池并发 返回wav数据转为mp3

class GPTSoVITS(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.copydata=copy.deepcopy(self.queue_tts)
        api_url = config.params['gptsovits_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
    def _exec(self):
        self._local_mul_thread()
    def _item_task(self,data_item:Union[Dict,List,None]):
        try:
            data_item=self.copydata.pop(0)
            if tools.vail_file(data_item['filename']):
                return True
        except:
            return True
        try:
            text = data_item['text'].strip()
            role=data_item['role']
            if not text:
                return True
            if text[-1] not in self.splits:
                text += '.'
            if len(text) < 4:
                text = f'。{text}，。'
            data = {
                "text": text,
                "text_language": "zh" if self.language.startswith('zh') else self.language,
                "extra": config.params['gptsovits_extra'],
                "ostype": sys.platform}
            if role:
                roledict = tools.get_gptsovits_role()
                if role in roledict:
                    data.update(roledict[role])
            # 克隆声音
            response = requests.post(f"{self.api_url}", json=data, proxies={"http": "", "https": ""}, timeout=3600)
            # 获取响应头中的Content-Type
            content_type = response.headers.get('Content-Type')

            if 'application/json' in content_type:
                # 如果是JSON数据，使用json()方法解析
                data = response.json()
                self.error=f"GPT-SoVITS返回错误信息-1:{data['message']}"
                return False

            if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                # 如果是WAV音频流，获取原始音频数据
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(response.content)
                time.sleep(1)
                if not os.path.exists(data_item['filename'] + ".wav"):
                    self.error=f'GPT-SoVITS合成声音失败-2:{text=}'
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
                Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error=''
            self.has_done+=1
            return  True
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