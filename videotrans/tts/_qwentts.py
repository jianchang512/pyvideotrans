import copy
import time

import dashscope
import requests
import urllib3

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

RETRY_NUMS = 2
RETRY_DELAY = 5


# 强制单线程 防止远端限制出错
@dataclass
class QWENTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        if not config.params['qwentts_key']:
            raise Exception(
                '必须在TTS设置 - Qwen TTS 中填写 API KEY ' if config.defaulelang == 'zh' else 'please input your Qwen TTS  API KEY')
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):

        role = data_item['role']
        # 主循环，用于无限重试连接错误
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                    model=config.params.get('qwentts_model', 'qwen-tts-latest'),
                    api_key=config.params.get('qwentts_key', ''),
                    text=data_item['text'],
                    voice=role,
                )

                if response is None:
                    self.error = "API call returned None response"
                    time.sleep(RETRY_DELAY)
                    continue

                if not hasattr(response, 'output') or response.output is None or not hasattr(response.output, 'audio'):
                    self.error = f"{response.message if hasattr(response, 'message') else str(response)}"
                    time.sleep(RETRY_DELAY)
                    continue

                resurl = requests.get(response.output.audio["url"])
                resurl.raise_for_status()  # 检查请求是否成功
                with open(data_item['filename'] + '.wav', 'wb') as f:
                    f.write(resurl.content)
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])

                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                # 任务成功，跳出 while True 循环并结束函数
                return
            except (requests.exceptions.ConnectionError, urllib3.exceptions.ProtocolError) as e:
                config.logger.exception(f'连接qwentts失败:{e}', exc_info=True)
                self._signal(text=f'连接QwenTTS失败,暂停30s后重试:{e}')
                time.sleep(30)
            except Exception as e:
                config.logger.exception(e, exc_info=True)
                self.error = str(e)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
