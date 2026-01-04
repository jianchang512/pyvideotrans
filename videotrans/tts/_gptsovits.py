import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict
from typing import Union, Set

import requests

from pydub import AudioSegment
from videotrans.configure import config
from videotrans.configure._except import  StopRetry
from videotrans.configure.config import tr
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class GPTSoVITS(BaseTTS):
    splits: Set[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        # 2. 处理并设置 api_url (同样是覆盖父类的值)
        api_url = config.params.get('gptsovits_url','').strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self._add_internal_host_noproxy(self.api_url)
        # 3. 初始化本类新增的属性
        self.splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit() or  not data_item.get('text','').strip()  or tools.vail_file(data_item['filename']):
            return
        role = data_item['role']
        if data_item["text"][-1] not in self.splits:
            data_item["text"] += '. '

        data = {
            "text": data_item['text'],
            "text_language": "zh" if self.language.startswith('zh') else self.language,
            "extra": config.params.get('gptsovits_extra',''),
            "ostype": sys.platform
        }

        roledict = tools.get_gptsovits_role()
        keys=list(roledict.keys())

        if role !='clone' and roledict and role in roledict:
            data.update(roledict[role])

        elif role == 'clone':#克隆原音频片段
            ref_wav=data_item.get('ref_wav','')
            if ref_wav and Path(ref_wav).exists():
                ref_wav_audio=AudioSegment.from_file(ref_wav)
                if len(ref_wav_audio)>=10000:#大于10s截断
                    ref_wav_audio[:9000].export(ref_wav)
                if len(ref_wav)>=3000:#大于3s合法
                    data['refer_wav_path'] = ref_wav
                    data['prompt_text'] = data_item.get('ref_text').strip()
                    data['prompt_language'] = data_item.get('ref_language','')

            if not data.get('refer_wav_path'):
                if keys[-1]=='clone':
                    # 无自定义参考音频，clone原音频时长不符合，失败
                    raise RuntimeError('No refer audio and origin audio duration not between 3-10s')
                # 克隆原音频失败，使用最后一个参考音频
                data.update(roledict[keys[-1]])

        if not data.get('refer_wav_path'):
            raise StopRetry(message=tr("Must pass in the reference audio file path"))

        if config.params.get('gptsovits_isv2',''):
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

        config.logger.debug(f'GPT-SoVITS get:{data=}\n{self.api_url=}')
        # 克隆声音
        response = requests.get(f"{self.api_url}", params=data,  timeout=3600)
        
        
        if response.ok:
            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                raise RuntimeError(f'GPT-SoVITS error-2')
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
        else:
            try:
                error_data = response.json() # 这里可以直接拿到 500 时的 JSON
                print("错误信息:", error_data)
            except:
                print("错误内容不是JSON:", response.text)
                error_data=response.text
            config.logger.debug(f'GPT-SoVITS return:{error_data=}')
            raise StopRetry(f"GPT-SoVITS error-1:{error_data}")

