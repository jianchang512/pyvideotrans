import copy
import os
import time
from pathlib import Path
from typing import Union, Dict, List

import httpx
import requests
from openai import OpenAI, APIConnectionError

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


class ChatterBoxTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['chatterbox_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        role = data_item['role']
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                if data_item.get('ref_wav') or (
                        role and role != 'chatterbox' and Path(f'{config.ROOT_DIR}/chatterbox/{role}').exists()):
                    # 克隆
                    self._item_task_clone(data_item['text'], role, data_item.get('ref_wav'), data_item['filename'])
                    self.has_done += 1
                    if self.inst and self.inst.precent < 80:
                        self.inst.precent += 0.1
                    return
                client = OpenAI(api_key='123456', base_url=self.api_url + '/v1',
                                http_client=httpx.Client(proxy=None, timeout=7200))
                response = client.audio.speech.create(
                    model="chatterbox-tts",  # 这是一个兼容性参数
                    voice=self.language,  # 这也是一个兼容性参数
                    input=data_item['text'],
                    speed=float(config.params["chatterbox_cfg_weight"]),  # 兼容，用于传递 cfg_weight
                    instructions=str(config.params["chatterbox_exaggeration"]),  # 兼容传递 exaggeration
                    response_format="mp3"  # 请求mp3格式
                )

                response.stream_to_file(data_item['filename'])
                self.has_done += 1
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except APIConnectionError as e:
                config.logger.exception(e, exc_info=True)
                self.error = '无法连接到 ChatterBox TTS 服务，请检查是否部署并启动 https://github.com/jianchang512/chatterbox-api 项目' if config.defaulelang == 'zh' else 'Unable to connect to ChatterBox TTS service. Please check whether the https://github.com/jianchang512/chatterbox-api project is deployed and started.'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                config.logger.exception(e, exc_info=True)
                error = str(e)
                self.error = error
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)

    def _item_task_clone(self, text, role, ref_wav=None, filename=None):
        import mimetypes
        if ref_wav:
            mime_type = 'audio/wav'
        else:
            ref_wav = f'{config.ROOT_DIR}/chatterbox/{role}'
            mime_type, _ = mimetypes.guess_type(ref_wav)
            # 如果无法根据扩展名猜出类型，则使用通用的二进制流类型作为备用
            if mime_type is None:
                mime_type = 'application/octet-stream'

        with open(ref_wav, 'rb') as audio_file:
            # 定义form-data中的文件部分
            # key 'audio_prompt' 必须与 Flask 服务器端 `request.files['audio_prompt']` 匹配
            files_payload = {
                'audio_prompt': (os.path.basename(ref_wav), audio_file, mime_type)
            }
            # 定义form-data中的文本部分
            # key 'input' 必须与 Flask 服务器端 `request.form['input']` 匹配
            form_data = {
                'input': text,
                'response_format': 'mp3',
                'cfg_weight': config.params["chatterbox_cfg_weight"],
                'exaggeration': config.params["chatterbox_exaggeration"],
                'language': self.language
            }
            # 发送POST请求，设置合理的超时时间
            response = requests.post(
                self.api_url + '/v2/audio/speech_with_prompt',
                data=form_data,
                files=files_payload,
                timeout=7200  # TTS可能需要一些时间，设置一个较长的超时
            )
            # 检查HTTP响应状态码，如果不是2xx，则会引发HTTPError
            response.raise_for_status()
            # 将返回的二进制音频内容写入文件
            with open(filename, 'wb') as output_file:
                output_file.write(response.content)
