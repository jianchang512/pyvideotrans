import os
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError


from gradio_client import Client, handle_file
from typing import List, Dict, Union

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class CosyVoice(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params['cosyvoice_url'].strip().rstrip('/').lower()
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self):
        self._local_mul_thread()

    def _item_task_cosyvoice2(self, data_item):

        text = data_item['text'].strip()
        if not text:
            return
        role = data_item['role']
        data = {'ref_wav': '','ref_text':data_item.get('ref_text','')}
        
        rolelist = tools.get_cosyvoice_role()

        if role not in rolelist:
            raise StopRetry(f'{role} 角色不存在')
        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
            data['ref_text'] = data_item.get('ref_text','')
        else:
            data['ref_wav'] = config.ROOT_DIR+"/f5-tts/"+rolelist[role].get('reference_audio','')
            data['ref_text'] = rolelist[role].get('reference_text','')

        if not Path(data['ref_wav']).exists():
            raise StopRetry(f"{data['ref_wav']} is not exists")
        
        config.logger.info(f'cosyvoice-tts {data=}')
        try:
            client = Client(self.api_url, ssl_verify=False)
        except Exception as e:
            raise StopRetry(str(e))

        result = client.predict(
            tts_text=text,
            prompt_wav_upload=handle_file(data['ref_wav']),
            prompt_wav_record=handle_file(data['ref_wav']),
            prompt_text=data.get('ref_text',''),
            instruct_text="",
            seed=0,
            stream="false",
            api_name="/generate_audio"

        )


        config.logger.info(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1

        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        

    def _item_cosyvoice_api(self, data_item):
        if not data_item.get('text',''):
            return
        rate = float(self.rate.replace('%', '')) / 100 if self.rate else 0
        role = data_item['role']

        api_url = self.api_url
        data = {
            "text": data_item['text'],
            "lang": "zh" if self.language.startswith('zh') else self.language,
            "speed": 1 + rate
        }
        rolelist = tools.get_cosyvoice_role()
        if role not in rolelist:
            raise StopRetry(f'预设角色 {role} 未在配置中找到')
        if role == 'clone':
            # 克隆音色
            # 原项目使用 clone_mul 跨语种克隆的方案，实际测试效果不如同语种，这地方修改成同语种克隆 /clone_eq
            ref_wav_path = data_item.get("ref_wav",'')
            if not Path(ref_wav_path).exists():
                raise StopRetry(f'不存在参考音频 {ref_wav_path}，无法使用clone功能' if config.defaulelang == 'zh' else f'No reference audio {ref_wav_path} exists')

            data['reference_text'] = data_item.get('ref_text','')
            data['reference_audio'] = self._audio_to_base64(ref_wav_path)
            api_url += '/clone_eq'
            data['encode'] = 'base64'
        else:
            role_info = rolelist[role]
            data['reference_audio'] = config.ROOT_DIR+"/f5-tts/"+role_info.get('reference_audio','')

            if not data['reference_audio']:
                raise StopRetry(f'预设角色 {role} 配置不正确，缺少克隆参考音频')

            # 检查是否存在参考文本，以决定使用哪个克隆接口
            reference_text = role_info.get('reference_text', '').strip()
            if reference_text:
                # 同时提供参考音频和文本，使用高质量同语种克隆
                data['reference_text'] = reference_text
                api_url += '/clone_eq'
            else:
                # 仅提供参考音频，使用跨语种克隆
                api_url += '/clone_mul'

        config.logger.info(f'请求数据：{api_url=},{data=}')
        # 克隆声音
        response = requests.post(f"{api_url}", data=data,  timeout=3600)
        response.raise_for_status()

        # 如果是WAV音频流，获取原始音频数据
        with open(data_item['filename'] + ".wav", 'wb') as f:
            f.write(response.content)
        time.sleep(1)
        if not os.path.exists(data_item['filename'] + ".wav"):
            raise RuntimeError(f'CosyVoice 合成声音失败-2')
        self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        
    def _item_task(self, data_item):
        if self._exit() or  not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)), wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO), after=after_log(config.logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
        
            # 兼容之前的 cosyvoice-api 接口
            if ":9233" not in self.api_url:
                self._item_task_cosyvoice2(data_item)
            else:
                self._item_cosyvoice_api(data_item)
        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error = e
            raise
