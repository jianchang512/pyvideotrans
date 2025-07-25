import copy
import re
import time
import requests
import urllib3
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
        self.dub_nums=1    
        self._local_mul_thread()
    
    def _item_task(self, data_item: dict = None):
        if not self.is_test and tools.vail_file(data_item['filename']):
            return
        text = data_item['text'].strip()
        role = data_item['role']
        if not text:
            return

        # 用于处理“其他错误”的重试计数器
        other_error_retries = 2

        # 主循环，用于无限重试连接错误
        while True:
            try:
                response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                    model=config.params.get('qwentts_model', 'qwen-tts-latest'),
                    api_key=config.params.get('qwentts_key', ''),
                    text=text,
                    voice=role,
                )

                if response is None:
                    raise RuntimeError("API call returned None response")

                if not hasattr(response,'output') or  response.output is None or not hasattr(response.output, 'audio'):
                    raise RuntimeError(f"{response.message if hasattr(response, 'message') else str(response)}")

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
                # 继续下一次循环，实现无限重试
                continue

            except Exception as e:
                config.logger.exception(e, exc_info=True)
                other_error_retries -= 1
                if other_error_retries > 0:
                    # 符合你的要求：其他错误暂停5秒
                    self._signal(text=f'发生未知错误，暂停5s后重试: {e}')
                    time.sleep(5)
                    # 继续下一次循环，进行重试
                    continue
                else:
                    # 如果其他错误的重试次数已用尽，则记录错误并抛出异常
                    self.error = str(e)
                    raise