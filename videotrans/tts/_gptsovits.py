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
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
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
        self.pad_audio=None
        self.speed = float(float(self.rate.replace('+', '').replace('-', '').replace('%', '')) / 100)
    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit() or  not data_item.get('text','').strip()  or tools.vail_file(data_item['filename']):
            return
        role = data_item['role']
        data = {
            "text": data_item['text'],
            "text_language": "zh" if self.language.startswith('zh') else self.language,
            "extra": config.params.get('gptsovits_extra',''),
            "ostype": sys.platform,

        }

        roledict = tools.get_gptsovits_role()
        keys=list(roledict.keys())
        ref_wav=data_item.get('ref_wav','')

        if role !='clone' and roledict and role in roledict:
            data.update(roledict[role])
        elif role == 'clone':#克隆原音频片段
            if ref_wav and Path(ref_wav).exists():
                data['prompt_text'] = data_item.get('ref_text').strip()
                data['prompt_language'] = data_item.get('ref_language','')
                data['refer_wav_path'] = ref_wav
                ref_wav_audio=AudioSegment.from_file(ref_wav,format="wav")
                ms_ref=len(ref_wav_audio)
                if ms_ref>9950:#大于10s截断
                    config.logger.warning(f'参考音频大于10s，需截断:{ref_wav=}')
                    ref_wav_audio[:9950].export(ref_wav,format="wav")
                elif ms_ref<3000:#大于3s合法
                    config.logger.warning(f'参考音频小于3s，末尾填空白:{ref_wav=}')
                    self.pad_audio= self.pad_audio if self.pad_audio else self._padforaudio(3000 if ms_ref<1500 else 1600)
                    (ref_wav_audio+self.pad_audio).export(ref_wav,format="wav")
            elif keys[-1]=='clone':
                # 无自定义参考音频，clone原音频时长不符合，失败
                raise RuntimeError('No refer audio and origin audio duration not between 3-10s')
            else:
                # 克隆原音频失败，使用最后一个参考音频
                data.update(roledict[keys[-1]])

        if not data.get('refer_wav_path') and role !='clone':
            raise StopRetry(message=tr("Must pass in the reference audio file path"))

        if config.params.get('gptsovits_isv2',''):
            data = {
                "text": data_item['text'],
                "text_lang": data.get('text_language', 'zh'),
                "ref_audio_path": data.get('refer_wav_path', ''),
                "prompt_text": data.get('prompt_text', ''),
                "prompt_lang": data.get('prompt_language', ''),
                "speed_factor": 1.0+self.speed,
                "text_split_method":"cut0"
            }

            if not self.api_url.endswith('/tts'):
                self.api_url += '/tts'
        else:
            data['speed']=1.0+self.speed
        config.logger.debug(f'GPT-SoVITS 当前需要发送的配音数据:{data=}\n{self.api_url=}')
        # 克隆声音
        response = requests.get(f"{self.api_url}", params=data,  timeout=3600,proxies={"https":"","http":""})

        if response.ok:
            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
            self.error=None
        else:
            try:
                error_data = response.json() # 这里可以直接拿到 500 时的 JSON
            except:
                error_data=response.text
            self.error=RuntimeError(error_data)
            config.logger.error(f'GPT-SoVITS {ref_wav=}\n返回错误:{error_data=}\n')
