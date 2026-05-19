import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Union
import requests
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatterBoxTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'http://' +params.get('chatterbox_url','').strip().rstrip('/').lower().replace('http://', '')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        try:
            ref_wav,_=self.get_ref_wav(data_item)
        except Exception:
            logger.debug('无参考音频，使用内置音色')
        else:
            return self._clone(data_item['text'], ref_wav, data_item['filename'])

        client = OpenAI(api_key='123456', base_url=self.api_url + '/v1')
        response = client.audio.speech.create(
            model="chatterbox-tts",  # 这是一个兼容性参数
            voice=self.language.split('-')[0],  # 这也是一个兼容性参数
            input=data_item['text'],
            speed=float(params.get("chatterbox_cfg_weight",'1.0')),  # 兼容，用于传递 cfg_weight
            instructions=str(params.get("chatterbox_exaggeration",'')),  # 兼容传递 exaggeration
            response_format="mp3"  # 请求mp3格式
        )

        response.stream_to_file(data_item['filename'] + ".mp3")
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])


    def _clone(self, text, ref_wav=None, filename=None):
        mime_type = 'audio/wav'
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
                'cfg_weight': params.get("chatterbox_cfg_weight",'0.3'),
                'exaggeration': params.get("chatterbox_exaggeration",''),
                'language': self.language.split('-')[0]
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
