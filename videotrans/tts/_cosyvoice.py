import copy
import os
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
class CosyVoice(BaseTTS):
    # ==================================================================
    # 1. 无需定义新字段。
    #    因为 `copydata`, `api_url`, `proxies` 都已在父类 BaseTTS 中
    #    用 field(init=False) 定义过。我们在这里只是为它们赋新值。
    # ==================================================================


    # ==================================================================
    # 2. 实现 __post_init__ 来处理本类的特定初始化逻辑
    # ==================================================================
    def __post_init__(self):
        # 关键第一步：调用父类的 __post_init__
        # 这将确保 BaseTTS 的所有初始化逻辑都已完成。
        # self.queue_tts 此时已经是深拷贝，self.copydata 此时是 []
        super().__post_init__()

        # --- 从这里开始，是 CosyVoice 的特定逻辑 ---

        # 将旧 __init__ 的逻辑迁移至此

        # 1. 为 self.copydata 赋值，这是本类特有的行为
        self.copydata = copy.deepcopy(self.queue_tts)

        # 2. 计算并覆盖父类中 api_url 的默认值
        api_url = config.params['cosyvoice_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')

        # 3. 覆盖父类中 proxies 的默认值
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):

        for attempt in range(RETRY_NUMS):
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                rate = float(self.rate.replace('%', '')) if self.rate else 0
                role = data_item['role']
                if self.api_url.endswith(':9880'):
                    data = {
                        "text": data_item['text'],
                        "speed": 1 + rate,
                        "new": 0,
                        "streaming": 0
                    }

                    rolelist = tools.get_cosyvoice_role()

                    if role == 'clone':
                        # 克隆音色
                        data['speaker'] = '中文女'
                    elif role in rolelist:
                        tmp = rolelist[role]
                        data['speaker'] = tmp if isinstance(tmp, str) or 'reference_audio' not in tmp else tmp[
                            'reference_audio']
                    else:
                        data['speaker'] = '中文女'

                    if data['speaker'] not in ["中文男", "中文女", "英文男", "英文女", "日语男", "韩语女", "粤语女"]:
                        data['new'] = 1

                    response = requests.post(f"{self.api_url}", json=data, proxies=self.proxies, timeout=3600)
                    response.raise_for_status()
                    config.logger.info(f'请求数据：{self.api_url=},{data=}')
                else:
                    api_url = self.api_url
                    data = {
                        "text": data_item['text'],
                        "lang": "zh" if self.language.startswith('zh') else self.language
                    }
                    rolelist = tools.get_cosyvoice_role()
                    if role == 'clone':
                        if not Path(data_item['ref_wav']).exists():
                            self.error = f'不存在参考音频，无法使用clone功能' if config.defaulelang == 'zh' else 'No reference audio exists and cannot use clone function'
                            return
                        # 克隆音色
                        data['reference_audio'] = self._audio_to_base64(data_item['ref_wav'])
                        api_url += '/clone_mul'
                        data['encode'] = 'base64'
                    elif role and role.endswith('.wav'):
                        data['reference_audio'] = rolelist[role]['reference_audio'] if role in rolelist else None
                        if not data['reference_audio']:
                            self.error = f'{role} 角色错误-2'
                            return
                        api_url += '/clone_mul'
                    elif role in rolelist:
                        data['role'] = rolelist[role]
                        api_url += '/tts'
                    else:
                        data['role'] = '中文女'
                    config.logger.info(f'请求数据：{api_url=},{data=}')
                    # 克隆声音
                    response = requests.post(f"{api_url}", data=data, proxies={"http": "", "https": ""}, timeout=3600)
                    response.raise_for_status()

                # 如果是WAV音频流，获取原始音频数据
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(response.content)
                time.sleep(1)
                if not os.path.exists(data_item['filename'] + ".wav"):
                    self.error = f'CosyVoice 合成声音失败-2'
                    time.sleep(RETRY_DELAY)
                    continue
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])

                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
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
