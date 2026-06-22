import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests
from pydub import AudioSegment
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, after_log, before_log, wait_fixed

from videotrans.configure.config import tr, params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


@dataclass
class GPTSoVITS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'http://' + params.get('gptsovits_url','').strip().rstrip('/').lower().replace('http://', '')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')
        self.speed = self.get_speed()
        self.roledict = tools.get_gptsovits_role() or {}

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = data_item['role']
        data = {
            "text": data_item['text'],
            "text_language": "zh" if self.language.startswith('zh') else self.language,
        }
        keys=list(self.roledict.keys())
        ref_wav=data_item.get('ref_wav','')

        if role !='clone' and self.roledict and role in self.roledict:
            data.update(self.roledict[role])
        elif role == 'clone':#克隆原音频片段
            if ref_wav:
                data['prompt_text'] = data_item.get('ref_text').strip()
                data['prompt_language'] = data_item.get('ref_language','')
                data['refer_wav_path'] = ref_wav
                ref_wav_audio=AudioSegment.from_file(ref_wav,format="wav")
                ms_ref=len(ref_wav_audio)
                if ms_ref>9990:#大于10s截断
                    logger.warning(f'参考音频大于10s，需截断:{ref_wav=}')
                    ref_wav_audio[:9990].export(ref_wav,format="wav")
                elif ms_ref<3000:#大于3s合法
                    logger.warning(f'参考音频小于3s，无法克隆，跳过:{ref_wav=}')
                    return tr('the reference audio duration is less than 3 seconds')
            else:
                return 'No reference audio available for voice cloning'+f"\n{self.api_url=}"
                
        
        if not data.get('refer_wav_path'):
            return tr("Must pass in the reference audio file path")+f"\n{self.api_url=}"

        if params.get('gptsovits_isv2',''):
            data = {
                "text": data_item['text'],
                "text_lang": data.get('text_language', 'zh'),
                "ref_audio_path": data.get('refer_wav_path', ''),
                "prompt_text": data.get('prompt_text', ''),
                "prompt_lang": data.get('prompt_language', ''),
                "speed_factor": self.speed,
                "text_split_method":"cut5"
            }

            if not self.api_url.endswith('/tts'):
                self.api_url += '/tts'
        else:
            data['speed']=1.0+self.speed
        logger.debug(f'GPT-SoVITS 当前需要发送的配音数据:{data=}\n{self.api_url=}')
        # 克隆声音
        try:
            response = requests.post(f"{self.api_url}", json=data,  timeout=3600,proxies={"https":"","http":""})
        except requests.exceptions.ConnectionError as e:
            if "Failed to establish a new connection" in str(e):
                raise StopTask(f"[GPT-SoVITS] {tr('This channel needs deployed and started before available')}") from e
        
        if response.ok:
            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
        else:
            error_data=response.text+f"\n{self.api_url=}"
            logger.error(f'GPT-SoVITS {ref_wav=}\n返回错误:{error_data=}\n')
            return error_data
