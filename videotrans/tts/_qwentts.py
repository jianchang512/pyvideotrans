import logging
import time
from dataclasses import dataclass

import dashscope
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

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

        # 主循环，用于无限重试连接错误
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            role = data_item['role']
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                model=config.params.get('qwentts_model', 'qwen-tts-latest'),
                api_key=config.params.get('qwentts_key', ''),
                text=data_item['text'],
                voice=role,
            )

            if response is None:
                self.error = "API call returned None response"
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            if not hasattr(response, 'output') or response.output is None or not hasattr(response.output, 'audio'):
                self.error = f"{response.message if hasattr(response, 'message') else str(response)}"
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)

            resurl = requests.get(response.output.audio["url"])
            resurl.raise_for_status()  # 检查请求是否成功
            with open(data_item['filename'] + '.wav', 'wb') as f:
                f.write(resurl.content)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
