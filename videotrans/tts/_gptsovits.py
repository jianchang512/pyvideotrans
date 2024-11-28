import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Union, Dict, List

import requests
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发 返回wav数据转为mp3

class GPTSoVITS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['gptsovits_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
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
            if text[-1] not in self.splits:
                text += '.'
            if len(text) < 4:
                text = f'。{text}，。'
            data = {
                "text": text,
                "text_language": "zh" if self.language.startswith('zh') else self.language,
                "extra": config.params['gptsovits_extra'],
                "ostype": sys.platform
            }
            #refer_wav_path
            #prompt_text
            #prompt_language
            if role:
                roledict = tools.get_gptsovits_role()

                if roledict and  role in roledict:
                    data.update(roledict[role])
            if config.params['gptsovits_isv2']:
                data={
                    "text":data['text'],
                    "text_lang":data.get('text_language','zh'),
                    "ref_audio_path":data.get('refer_wav_path',''),
                    "prompt_text":data.get('prompt_text',''),
                    "prompt_lang":data.get('prompt_language',''),
                    "speed_factor":1.0
                }
                speed=float(float(self.rate.replace('+','').replace('-','').replace('%',''))/100)
                if speed>0:
                    data['speed_factor']+=speed

                if not self.api_url.endswith('/tts'):
                    self.api_url+='/tts'
            config.logger.info(f'GPT-SoVITS post:{data=}\n{self.api_url=}')
            # 克隆声音
            response = requests.post(f"{self.api_url}", json=data, proxies=self.proxies, timeout=3600)
            if response.status_code != 200:
                self.error = f'GPT-SoVITS合成声音失败: status_code={response.status_code} {response.reason} {response.text}'
                return
            # 获取响应头中的Content-Type
            content_type = response.headers.get('Content-Type')

            if 'application/json' in content_type:
                # 如果是JSON数据，使用json()方法解析
                data = response.json()
                config.logger.info(f'GPT-SoVITS return:{data=}')
                self.error = f"GPT-SoVITS返回错误信息-1:{data}"
                return

            if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                # 如果是WAV音频流，获取原始音频数据
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(response.content)
                time.sleep(1)
                if not os.path.exists(data_item['filename'] + ".wav"):
                    self.error = f'GPT-SoVITS合成声音失败-2:{text=}'
                    return
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
                try:
                    Path(data_item['filename'] + ".wav").unlink(missing_ok=True)
                except CouldntDecodeError:
                    config.logger.info(f'GPT-SoVITS 配音失败')
                    self.error = f"GPT-SoVITS返回错误信息"
                    return

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
