import copy
import re
import time
import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import dashscope

# 强制单线程 防止远端限制出错

class QWENTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.pro=None

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        if not config.params['qwentts_key']:
            raise Exception('必须在TTS设置 - Qwen TTS 中填写 API KEY ' if config.defaulelang=='zh' else 'please input your Qwen TTS  API KEY')
        self._local_mul_thread()
    def _item_task(self, data_item: dict = None):
        if not self.is_test and tools.vail_file(data_item['filename']):
            return
        text = data_item['text'].strip()
        role = data_item['role']
        if not text:
            return

        try:
            response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                model=config.params.get('qwentts_model', 'qwen-tts-latest'),
                api_key=config.params.get('qwentts_key', ''),
                text=text,
                voice=role,
            )

            # Check if response is None
            if response is None:
                raise RuntimeError("API call returned None response")

            # Check if response.output is None
            if response.output is None:
                raise RuntimeError(f"API call failed: response.output is None,{response.message}")

            # Check if response.output.audio exists
            if not hasattr(response.output, 'audio') or response.output.audio is None:
                raise RuntimeError(f"API call failed: response.output.audio is None or missing,{response.message}")

            resurl = requests.get(response.output.audio["url"])
            resurl.raise_for_status()  # 检查请求是否成功
            with open(data_item['filename']+'.wav', 'wb') as f:
                f.write(resurl.content)
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            error = str(e)
            self.error = error


