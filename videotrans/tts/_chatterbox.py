import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatterBoxTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        api_url = config.params.get('chatterbox_url','').strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit() or  not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            role = data_item['role']
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            if data_item.get('ref_wav') or (
                    role and role != 'chatterbox' and Path(f'{config.ROOT_DIR}/chatterbox/{role}').exists()):
                # 克隆
                self._item_task_clone(data_item['text'], role, data_item.get('ref_wav'), data_item['filename'])
                return
            client = OpenAI(api_key='123456', base_url=self.api_url + '/v1')
            response = client.audio.speech.create(
                model="chatterbox-tts",  # 这是一个兼容性参数
                voice=self.language.split('-')[0],  # 这也是一个兼容性参数
                input=data_item['text'],
                speed=float(config.params.get("chatterbox_cfg_weight",'1.0')),  # 兼容，用于传递 cfg_weight
                instructions=str(config.params.get("chatterbox_exaggeration",'')),  # 兼容传递 exaggeration
                response_format="mp3"  # 请求mp3格式
            )

            response.stream_to_file(data_item['filename'] + ".mp3")
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])

        _run()

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
                'cfg_weight': config.params.get("chatterbox_cfg_weight",'0.3'),
                'exaggeration': config.params.get("chatterbox_exaggeration",''),
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
            with open(filename + ".mp3", 'wb') as output_file:
                output_file.write(response.content)
            self.convert_to_wav(filename + ".mp3", filename)
