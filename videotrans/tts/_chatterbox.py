import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Union, Dict, List

import httpx
import requests
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from openai import OpenAI, RateLimitError, APIConnectionError


# 线程池并发 返回wav数据转为mp3

class ChatterBoxTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['chatterbox_url'].strip().rstrip('/').lower()
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
            if  data_item.get('ref_wav') or  (role and role !='chatterbox' and Path(f'{config.ROOT_DIR}/chatterbox/{role}').exists()):
                # 克隆
                return self._item_task_clone(data_item)
                
            

            client = OpenAI(api_key='123456', base_url=self.api_url+'/v1',
                            http_client=httpx.Client(proxy=None,timeout=7200))
            response = client.audio.speech.create(
                model="chatterbox-tts",  # 这是一个兼容性参数
                voice=self.language,           # 这也是一个兼容性参数
                input=text,
                speed=float(config.params["chatterbox_cfg_weight"]),# 兼容，用于传递 cfg_weight
                instructions=str(config.params["chatterbox_exaggeration"]), # 兼容传递 exaggeration
                response_format="mp3"    # 请求mp3格式
            )
                
            response.stream_to_file(data_item['filename'])
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        except APIConnectionError as e:
            config.logger.exception(e, exc_info=True)
            
            self.error='无法连接到 ChatterBox TTS 服务，请检查是否部署并启动 https://github.com/jianchang512/chatterbox-api 项目' if config.defaulelang == 'zh' else 'Unable to connect to ChatterBox TTS service. Please check whether the https://github.com/jianchang512/chatterbox-api project is deployed and started.'

        except Exception as e:
            config.logger.exception(e, exc_info=True)
            error = str(e)
            self.error = error
    
    def _item_task_clone(self,data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            import mimetypes 
            text = data_item['text'].strip()
            if not text:
                return
            if data_item.get('ref_wav'):
                role_file=data_item.get('ref_wav')
                mime_type='audio/wav'
            else:
                role = data_item['role']
                role_file=f'{config.ROOT_DIR}/chatterbox/{role}'
                # 
                mime_type, _ = mimetypes.guess_type(role_file)
                # 如果无法根据扩展名猜出类型，则使用通用的二进制流类型作为备用
                if mime_type is None:
                    mime_type = 'application/octet-stream'
            with open(role_file, 'rb') as audio_file:
                # 定义form-data中的文件部分
                # key 'audio_prompt' 必须与 Flask 服务器端 `request.files['audio_prompt']` 匹配
                files_payload = {
                    'audio_prompt': (os.path.basename(role), audio_file, mime_type)
                }
                
                # 定义form-data中的文本部分
                # key 'input' 必须与 Flask 服务器端 `request.form['input']` 匹配
                form_data = {
                    'input': text,
                    'response_format':'mp3',
                    'cfg_weight':config.params["chatterbox_cfg_weight"],
                    'exaggeration':config.params["chatterbox_exaggeration"],
                    'language':self.language
                }


                
                # 发送POST请求，设置合理的超时时间
                response = requests.post(
                    self.api_url+'/v2/audio/speech_with_prompt', 
                    data=form_data, 
                    files=files_payload,
                    timeout=7200  # TTS可能需要一些时间，设置一个较长的超时
                )

                # 检查HTTP响应状态码，如果不是2xx，则会引发HTTPError
                response.raise_for_status()


                # 将返回的二进制音频内容写入文件
                with open(data_item['filename'], 'wb') as output_file:
                    output_file.write(response.content)
           
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        except requests.exceptions.RequestException as e:
            config.logger.exception(e, exc_info=True)
            print(f"\n❌ An error occurred during the request: {e}")
            error =  '无法连接到 ChatterBox TTS 服务，请检查是否部署并启动 https://github.com/jianchang512/chatterbox-api 项目' if config.defaulelang == 'zh' else 'Unable to connect to ChatterBox TTS service. Please check whether the https://github.com/jianchang512/chatterbox-api project is deployed and started.' 
            self.error = error+str(e)
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            error = str(e)
            self.error = error