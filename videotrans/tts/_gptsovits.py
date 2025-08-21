import os
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Dict
from typing import Union, Set

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class GPTSoVITS(BaseTTS):
    splits: Set[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self.proxies = {"http": "", "https": ""}

        # 2. 处理并设置 api_url (同样是覆盖父类的值)
        api_url = config.params['gptsovits_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

        # 3. 初始化本类新增的属性
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            role = data_item['role']

            if data_item["text"][-1] not in self.splits:
                data_item["text"] += '.'
            if len(data_item["text"]) < 4:
                data_item["text"] = f'。{data_item["text"]}，。'
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            data = {
                "text": data_item['text'],
                "text_language": "zh" if self.language.startswith('zh') else self.language,
                "extra": config.params['gptsovits_extra'],
                "ostype": sys.platform
            }
            print(f'{data=}')
            # refer_wav_path
            # prompt_text
            # prompt_language
            if role:
                roledict = tools.get_gptsovits_role()

                if roledict and role in roledict:
                    data.update(roledict[role])
            if config.params['gptsovits_isv2']:
                data = {
                    "text": data_item['text'],
                    "text_lang": data.get('text_language', 'zh'),
                    "ref_audio_path": data.get('refer_wav_path', ''),
                    "prompt_text": data.get('prompt_text', ''),
                    "prompt_lang": data.get('prompt_language', ''),
                    "speed_factor": 1.0
                }
                speed = float(float(self.rate.replace('+', '').replace('-', '').replace('%', '')) / 100)
                if speed > 0:
                    data['speed_factor'] += speed

                if not self.api_url.endswith('/tts'):
                    self.api_url += '/tts'

            config.logger.info(f'GPT-SoVITS get:{data=}\n{self.api_url=}')
            # 克隆声音
            response = requests.get(f"{self.api_url}", params=data, proxies={"http": "", "https": ""}, timeout=3600)

            response.raise_for_status()
            # 获取响应头中的Content-Type
            content_type = response.headers.get('Content-Type')

            if 'application/json' in content_type:
                # 如果是JSON数据，使用json()方法解析
                data = response.json()
                config.logger.info(f'GPT-SoVITS return:{data=}')
                self.error = f"GPT-SoVITS返回错误信息-1:{data}"
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                # 如果是WAV音频流，获取原始音频数据
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(response.content)
                time.sleep(1)
                if not os.path.exists(data_item['filename'] + ".wav"):
                    self.error = f'GPT-SoVITS合成声音失败-2'
                    time.sleep(RETRY_DELAY)
                    raise RuntimeError(self.error)
                self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
