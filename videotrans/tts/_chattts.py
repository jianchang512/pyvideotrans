import copy
import re
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatTTS(BaseTTS):
    # ==================================================================
    # 1. ChatTTS 没有引入新的、需要预先声明的字段。
    #    它只是修改了从父类继承来的字段的值。
    #    因此，我们不需要在这里添加新的 field 定义。
    # ==================================================================


    # ==================================================================
    # 2. 实现 __post_init__ 来处理本类的特定初始化逻辑和覆盖操作。
    # ==================================================================
    def __post_init__(self):
        # 关键第一步：调用父类的 __post_init__。
        # 这将确保 BaseTTS 的所有初始化逻辑（包括对 copydata, api_url, proxies 的初始赋值）都已完成。
        super().__post_init__()

        # --- 从这里开始，是 ChatTTS 的特定逻辑，它会覆盖父类的某些设置 ---

        # 1. 覆盖属性
        # 您的旧代码再次执行了 deepcopy，我们保留这个行为。
        self.copydata = copy.deepcopy(self.queue_tts)

        # 从配置中读取并处理 API URL
        api_url = config.params['chattts_api'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '').replace('/tts', '')

        # 为代理设置一个具体的值
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                data = {"text": data_item['text'], "voice": data_item['role'], 'prompt': '', 'is_split': 1}
                res = requests.post(f"{self.api_url}/tts", data=data, proxies=self.proxies, timeout=3600)
                res.raise_for_status()
                config.logger.info(f'chatTTS:{data=}')
                res = res.json()
                if res is None:
                    self.error = 'ChatTTS端出错，请查看其控制台终端'
                    time.sleep(RETRY_DELAY)
                    continue

                if "code" not in res or res['code'] != 0:
                    if "msg" in res:
                        Path(data_item['filename']).unlink(missing_ok=True)
                    self.error = f'{res}'
                    time.sleep(RETRY_DELAY)
                    continue

                if self.api_url.find('127.0.0.1') > -1 or self.api_url.find('localhost') > -1:
                    tools.wav2mp3(re.sub(r'\\{1,}', '/', res['filename']), data_item['filename'])
                    if self.inst and self.inst.precent < 80:
                        self.inst.precent += 0.1
                    self.has_done += 1
                    self.error = ''
                    self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                    return

                resb = requests.get(res['url'])
                resb.raise_for_status()

                config.logger.info(f'ChatTTS:resb={resb.status_code=}')
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(resb.content)
                time.sleep(1)
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
                Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.has_done += 1
                self.error = ''
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except (requests.ConnectionError, requests.Timeout) as e:
                config.logger.exception(e,exc_info=True)
                self.error = "连接失败，请检查是否启动了api服务" if config.defaulelang == 'zh' else 'Connection failed, please check if the api service is started'
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
            except Exception as e:
                self.error = str(e)
                config.logger.exception(e, exc_info=True)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
