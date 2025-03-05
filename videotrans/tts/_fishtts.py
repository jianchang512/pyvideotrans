import copy
import json
import os
import time
from pathlib import Path
from typing import Union, Dict, List

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发  返回wav数据转为mp3
class FishTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['fishtts_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.proxies={"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return

        try:
            text = data_item['text'].strip()
            role = data_item['role']
            if not text:
                return
            roledict = tools.get_fishtts_role()
            if not role or not roledict.get(role):
                raise Exception('必须在设置中填写参考音频路径名、参考音频对应的文字')
            data = {"text": text, "references":[ {"audio":"","text": roledict[role]['reference_text']} ] }
            
            # 克隆声音
            audio_path=f'{config.ROOT_DIR}/{roledict[role]["reference_audio"]}'
            if os.path.exists(audio_path):
                data['references'][0]['audio']=self._audio_to_base64(audio_path)
            else:
                raise Exception(f'参考音频不存在:{audio_path}\n请确保该音频存在')

            config.logger.info(f'fishTTS-post:{data=},{self.proxies=}')
            response = requests.post(f"{self.api_url}", json=data, proxies=self.proxies, timeout=3600)
            if response.status_code != 200:
                self.error = f'status_code={response.status_code} {response.reason} {response.text}'
                return

            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'FishTTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
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
        return
