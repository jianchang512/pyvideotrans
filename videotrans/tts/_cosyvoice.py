import os
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class CosyVoice(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        api_url = config.params['cosyvoice_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        # 3. 覆盖父类中 proxies 的默认值
        self.proxies = {"http": "", "https": ""}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            rate = float(self.rate.replace('%', '')) / 100 if self.rate else 0
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
                    "lang": "zh" if self.language.startswith('zh') else self.language,
                    "speed": 1 + rate
                }
                rolelist = tools.get_cosyvoice_role()
                if role == 'clone':
                    # 克隆音色
                    # 原项目使用 clone_mul 跨语种克隆的方案，实际测试效果不如同语种，这地方修改成同语种克隆 /clone_eq
                    # 否则后面的elif代码留着干嘛用？
                    ref_wav_info = data_item['ref_wav'].split('#')
                    ref_wav_path = ref_wav_info[0]
                    reference_text = ref_wav_info[1] if len(ref_wav_info) > 1 else ''

                    if not Path(ref_wav_path).exists():
                        self.error = f'不存在参考音频 {ref_wav_path}，无法使用clone功能' if config.defaulelang == 'zh' else f'No reference audio {ref_wav_path} exists'
                        return

                    if not reference_text:
                        raise ValueError(f"参考音频 '{ref_wav_path}' 缺少#后的参考文本，无法使用同语种克隆")

                    data['reference_text'] = reference_text
                    data['reference_audio'] = self._audio_to_base64(ref_wav_path)
                    api_url += '/clone_eq'
                    data['encode'] = 'base64'
                elif role and role.endswith('.wav'):
                    if role not in rolelist:
                        self.error = f'预设角色 {role} 未在配置中找到'
                        return

                    role_info = rolelist[role]
                    data['reference_audio'] = role_info.get('reference_audio')

                    if not data['reference_audio']:
                        self.error = f'预设角色 {role} 配置不正确，缺少克隆参考音频'
                        return

                    # 检查是否存在参考文本，以决定使用哪个克隆接口
                    reference_text = role_info.get('reference_text', '').strip()
                    if reference_text:
                        # 同时提供参考音频和文本，使用高质量同语种克隆
                        data['reference_text'] = reference_text
                        api_url += '/clone_eq'
                        print('CosyVoice 使用同语种克隆 /clone_eq')
                    else:
                        # 仅提供参考音频，使用跨语种克隆
                        api_url += '/clone_mul'
                        print('CosyVoice 使用跨语种克隆 /clone_mul')
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
                raise RuntimeError(self.error)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()
