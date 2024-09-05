
import copy
import os

import time
from pathlib import Path

import requests

from videotrans.configure import config

from videotrans.tts._base import BaseTTS
from videotrans.util import tools



# 线程池并发 返回wav数据转为mp3

class CosyVoice(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.copydata=copy.deepcopy(self.queue_tts)
        api_url = config.params['cosyvoice_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')


    def _exec(self):
        self._local_mul_thread()

    def _item_task(self,data_item:dict=None):
        if not data_item or tools.vail_file(data_item['filename']):
            return True
        try:
            text = data_item['text'].strip()
            if not text:
                return True
            rate = float(self.rate.replace('%', '')) if self.rate else 0
            role=data_item['role']
            if self.api_url.endswith(':9880'):
                data = {
                    "text": text,
                    "speed": 1 + rate,
                    "new": 0,
                    "streaming": 0
                }

                rolelist = tools.get_cosyvoice_role()

                if role == 'clone':
                    # 克隆音色
                    data['speaker'] = '中文女'
                elif role in rolelist:
                    tmp = rolelist[role]
                    data['speaker'] = tmp if isinstance(tmp, str) or 'reference_audio' not in tmp else tmp[
                        'reference_audio']
                else:
                    data['speaker'] = '中文女'

                if data['speaker'] not in ["中文男", "中文女", "英文男", "英文女", "日语男", "韩语女", "粤语女"]:
                    data['new'] = 1

                response = requests.post(f"{self.api_url}", json=data, proxies={"http": "", "https": ""}, timeout=3600)
                config.logger.info(f'请求数据：{self.api_url=},{data=}')
            else:
                api_url=self.api_url
                data = {
                    "text": text,
                    "lang": "zh" if self.language.startswith('zh') else self.language
                }
                rolelist = tools.get_cosyvoice_role()
                if role == 'clone':
                    # 克隆音色
                    data['reference_audio'] = self._audio_to_base64(data_item['filename'])
                    api_url += '/clone_mul'
                    data['encode'] = 'base64'
                elif role and role.endswith('.wav'):
                    data['reference_audio'] = rolelist[role]['reference_audio'] if role in rolelist else None
                    if not data['reference_audio']:
                        raise Exception(f'{role} 角色错误-2')
                    api_url += '/clone_mul'
                elif role in rolelist:
                    data['role'] = rolelist[role]
                    api_url += '/tts'
                else:
                    data['role'] = '中文女'
                config.logger.info(f'请求数据：{api_url=},{data=}')
                # 克隆声音
                response = requests.post(f"{api_url}", data=data, proxies={"http": "", "https": ""}, timeout=3600)

            if response.status_code != 200:
                # 如果是JSON数据，使用json()方法解析
                data = response.json()
                self.error=(f"CosyVoice 返回错误信息-1:{data['msg']}")
                return False

            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error=f'CosyVoice 合成声音失败-2:{text=}'
                return False
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

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

