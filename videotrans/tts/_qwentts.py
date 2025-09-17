import logging
import time
from dataclasses import dataclass

import dashscope
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
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
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
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
                time.sleep(RETRY_DELAY)
                raise RuntimeError("API call returned None response")

            if not hasattr(response, 'output') or response.output is None or not hasattr(response.output, 'audio'):
                time.sleep(RETRY_DELAY)
                raise RuntimeError( f"{response.message if hasattr(response, 'message') else str(response)}")

            resurl = requests.get(response.output.audio["url"])
            resurl.raise_for_status()  # 检查请求是否成功
            with open(data_item['filename'] + '.wav', 'wb') as f:
                f.write(resurl.content)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error = e
